import logging
import time

import asyncpg

from .introspeccao import citar, partir, qualificar

registro = logging.getLogger("kpi")

LIMITE_QUEBRA = 10
TEMPO_CONSULTA = 4000
ORCAMENTO = 6

AGREGACOES = {
    "soma": "sum({})",
    "media": "avg({})",
    "contagem": "count(*)",
    "distintos": "count(distinct {})",
    "minimo": "min({})",
    "maximo": "max({})",
}

# Inicio da janela, da anterior e balde da serie; hoje conta, entao 7d comeca 6 dias atras.
JANELAS: dict[str, tuple[str, str, str]] = {
    "7d": ("current_date - 6", "current_date - 13", "day"),
    "30d": ("current_date - 29", "current_date - 59", "day"),
    "90d": ("current_date - 89", "current_date - 179", "week"),
    "12m": ("current_date - 364", "current_date - 729", "month"),
    "tudo": ("", "", "month"),
}
JANELA_PADRAO = "30d"
LIMITE_SERIE = 400

SEM_CAMPO = "escolha o campo do indicador"
SEM_COLUNA = "a coluna não existe mais na tabela"
SEM_NUMERO = "a coluna não guarda número"
SEM_TEMPO = "o banco demorou demais, atualize para tentar de novo"
CAIU = "a conexão com o banco caiu"
FALHOU = "o banco recusou a consulta"


class Impossivel(Exception):
    pass


def janela_de(nome: str | None) -> tuple[str, str, str]:
    return JANELAS.get(nome or "", JANELAS[JANELA_PADRAO])


def _conta(indicador) -> str:
    return AGREGACOES[indicador.agregacao].format(citar(indicador.coluna or ""))


def _filtro(coluna: str | None, inicio: str, fim: str = "") -> str:
    if not coluna or not inicio:
        return ""
    return f"{citar(coluna)} >= {inicio}{fim}"


def _onde(coluna: str | None, inicio: str, fim: str = "") -> str:
    condicao = _filtro(coluna, inicio, fim)
    return f" where {condicao}" if condicao else ""


def _numero(valor) -> float | None:
    try:
        return None if valor is None else float(valor)
    except (TypeError, ValueError):
        raise Impossivel(SEM_NUMERO) from None


def variacao(agora: float | None, antes: float | None) -> float | None:
    if agora is None or not antes:
        return None
    return (agora - antes) / abs(antes) * 100


def _caiu(erro: Exception) -> bool:
    return isinstance(erro, asyncpg.PostgresConnectionError | asyncpg.InterfaceError)


def _fonte(tabela: str, calculados: list[tuple[str, str]] | None) -> str:
    if not calculados:
        return qualificar(*partir(tabela))
    base = qualificar(*partir(tabela))
    fonte = base
    for nome, formula in calculados:
        fonte = f"(select *, ({formula}) as {citar(nome)} from {fonte}) as c"
    return fonte


def _falha(erro: Exception) -> dict:
    if isinstance(erro, Impossivel):
        return {"erro": str(erro)}
    if isinstance(erro, asyncpg.UndefinedColumnError):
        return {"erro": SEM_COLUNA}
    if isinstance(erro, asyncpg.QueryCanceledError):
        return {"erro": SEM_TEMPO}
    if _caiu(erro):
        return {"erro": CAIU}
    if isinstance(erro, asyncpg.PostgresError):
        registro.warning("o banco do cliente recusou a consulta: %s", erro)
        return {"erro": FALHOU}
    registro.exception("falha inesperada ao calcular")
    return {"erro": "não foi possível calcular"}


async def _valores(
    conexao, de: str, atual: str, antes: str, grupo: list, onde_atual: str = ""
) -> dict:
    def conta(indicador, filtro: str) -> str:
        base = _conta(indicador)
        return f"{base} filter (where {filtro})" if filtro else base

    campos = []
    for n, indicador in enumerate(grupo):
        if antes:
            campos.append(f"{conta(indicador, antes)} as a{n}")
        campos.append(f"{conta(indicador, atual)} as v{n}")
    campos = ", ".join(campos)

    try:
        linha = await conexao.fetchrow(f"select {campos} from {de}")
    except Exception as e:  # noqa: BLE001 - refaz um a um para o erro ficar no indicador
        if _caiu(e) or isinstance(e, asyncpg.QueryCanceledError):
            return {str(i.id): _falha(e) for i in grupo}
        saida: dict[str, dict] = {}
        for indicador in grupo:
            try:
                bruto = await conexao.fetchval(
                    f"select {_conta(indicador)} from {de}{onde_atual}"
                )
                saida[str(indicador.id)] = {"valor": _numero(bruto)}
            except Exception as outro:  # noqa: BLE001 - um não derruba os outros
                saida[str(indicador.id)] = _falha(outro)
        return saida

    saida = {}
    for n, indicador in enumerate(grupo):
        try:
            agora = _numero(linha[f"v{n}"])
            antes_ = _numero(linha[f"a{n}"]) if antes else None
        except Impossivel as e:
            saida[str(indicador.id)] = {"erro": str(e)}
            continue
        saida[str(indicador.id)] = {
            "valor": agora,
            "anterior": antes_,
            "variacao": variacao(agora, antes_),
        }
    return saida


async def _serie(conexao, de: str, onde: str, coluna: str, balde: str, conta: str):
    return [
        {"rotulo": r["rotulo"] or "sem valor", "valor": _numero(r["valor"])}
        for r in await conexao.fetch(
            f"select date_trunc('{balde}', {citar(coluna)})::date::text as rotulo,"
            f" {conta} as valor from {de}{onde} group by 1 order by 1"
            f" limit {LIMITE_SERIE}"
        )
    ]


async def _serie_com_anterior(
    conexao, de: str, coluna: str, inicio: str, inicio_anterior: str, balde: str, conta
):
    tempo = citar(coluna)
    passo = f"(({inicio}) - ({inicio_anterior})) * interval '1 day'"
    alinhado = f"case when {tempo} >= {inicio} then {tempo} else {tempo} + {passo} end"
    linhas = await conexao.fetch(
        f"select date_trunc('{balde}', {alinhado})::date::text as rotulo,"
        f" {conta} filter (where {tempo} >= {inicio}) as valor,"
        f" {conta} filter (where {tempo} < {inicio}) as anterior"
        f" from {de} where {tempo} >= {inicio_anterior}"
        f" group by 1 order by 1 limit {LIMITE_SERIE}"
    )
    return [
        {
            "rotulo": r["rotulo"],
            "valor": _numero(r["valor"]),
            "anterior": _numero(r["anterior"]),
        }
        for r in linhas
    ]


async def calcular(
    conexao: asyncpg.Connection,
    tabela: str,
    indicadores,
    janela: str | None = None,
    com_serie: bool = True,
    calculados: list[tuple[str, str]] | None = None,
) -> dict:
    await conexao.execute(f"set statement_timeout = {TEMPO_CONSULTA}")
    prazo = time.monotonic() + ORCAMENTO
    de = _fonte(tabela, calculados)
    inicio, inicio_anterior, balde = janela_de(janela)

    com_campo = {
        str(i.id) for i in indicadores if i.agregacao == "contagem" or i.coluna
    }
    validos = [i for i in indicadores if str(i.id) in com_campo]
    resultados: dict[str, dict] = {
        str(i.id): {"erro": SEM_CAMPO}
        for i in indicadores
        if str(i.id) not in com_campo
    }
    if not validos:
        return resultados

    com_tempo = [i for i in validos if i.tempo]
    sem_tempo = [i for i in validos if not i.tempo]

    por_tempo: dict[str, list] = {}
    for indicador in com_tempo:
        por_tempo.setdefault(indicador.tempo, []).append(indicador)
    for tempo, grupo in por_tempo.items():
        if time.monotonic() > prazo:
            resultados.update({str(i.id): {"erro": SEM_TEMPO} for i in grupo})
            continue
        atual = _filtro(tempo, inicio)
        antes = (
            _filtro(tempo, inicio_anterior, f" and {citar(tempo)} < {inicio}")
            if inicio_anterior
            else ""
        )
        resultados.update(
            await _valores(conexao, de, atual, antes, grupo, _onde(tempo, inicio))
        )
    if sem_tempo:
        resultados.update(await _valores(conexao, de, "", "", sem_tempo))

    for indicador in sem_tempo:
        resultados[str(indicador.id)]["serie"] = []

    if not com_serie:
        for indicador in com_tempo:
            resultados[str(indicador.id)]["serie"] = []
        return resultados

    for indicador in com_tempo:
        dados = resultados[str(indicador.id)]
        if "erro" in dados or time.monotonic() > prazo:
            dados["serie"] = []
            continue
        try:
            if inicio_anterior:
                dados["serie"] = await _serie_com_anterior(
                    conexao,
                    de,
                    indicador.tempo,
                    inicio,
                    inicio_anterior,
                    balde,
                    _conta(indicador),
                )
            else:
                dados["serie"] = await _serie(
                    conexao,
                    de,
                    _onde(indicador.tempo, inicio),
                    indicador.tempo,
                    balde,
                    _conta(indicador),
                )
        except Exception:  # noqa: BLE001 - sem serie o numero ainda serve
            registro.exception("falha na serie de %s", indicador.nome)
            dados["serie"] = []
    return resultados


async def compor(
    conexao: asyncpg.Connection,
    tabela: str,
    indicador,
    dimensao: str,
    janela: str | None = None,
    limite: int = LIMITE_QUEBRA,
    calculados: list[tuple[str, str]] | None = None,
) -> tuple[list[dict], float | None]:
    if indicador.agregacao != "contagem" and not indicador.coluna:
        raise Impossivel(SEM_CAMPO)
    await conexao.execute(f"set statement_timeout = {TEMPO_CONSULTA}")
    inicio, inicio_anterior, _ = janela_de(janela)
    aditivo = indicador.agregacao in ("soma", "contagem")
    conta = _conta(indicador)
    comparar = bool(indicador.tempo and inicio_anterior)
    if comparar:
        tempo = citar(indicador.tempo)
        valor = f"{conta} filter (where {tempo} >= {inicio})"
        anterior = f", {conta} filter (where {tempo} < {inicio}) as anterior"
        onde = f" where {tempo} >= {inicio_anterior}"
    else:
        valor, anterior, onde = conta, "", _onde(indicador.tempo, inicio)
    total = f", sum({valor}) over () as total" if aditivo else ""
    try:
        linhas = await conexao.fetch(
            f"select {citar(dimensao)}::text as rotulo, {valor} as valor"
            f"{anterior}{total} from {_fonte(tabela, calculados)}{onde} group by 1"
            f" order by 2 desc nulls last limit {int(limite)}",
        )
    except asyncpg.UndefinedColumnError:
        raise Impossivel(SEM_COLUNA) from None
    except asyncpg.QueryCanceledError:
        raise Impossivel(SEM_TEMPO) from None
    pontos = [
        {
            "rotulo": r["rotulo"] or "sem valor",
            "valor": _numero(r["valor"]),
            "anterior": _numero(r["anterior"]) if comparar else None,
        }
        for r in linhas
        if r["valor"] is not None
    ]
    return pontos, _numero(linhas[0]["total"]) if aditivo and linhas else None


async def mudancas(
    conexao: asyncpg.Connection,
    tabela: str,
    indicador,
    dimensoes: list[str],
    janela: str | None = None,
    calculados: list[tuple[str, str]] | None = None,
) -> list[dict]:
    inicio, inicio_anterior, _ = janela_de(janela)
    if not indicador.tempo or not inicio_anterior:
        raise Impossivel("compare com um período que tenha anterior, como 30 dias")
    if indicador.agregacao != "contagem" and not indicador.coluna:
        raise Impossivel(SEM_CAMPO)
    await conexao.execute(f"set statement_timeout = {TEMPO_CONSULTA}")
    tempo = citar(indicador.tempo)
    conta = _conta(indicador)
    de = _fonte(tabela, calculados)
    fatores = []
    for dimensao in dimensoes:
        try:
            linhas = await conexao.fetch(
                f"select {citar(dimensao)}::text as grupo,"
                f" {conta} filter (where {tempo} >= {inicio}) as valor,"
                f" {conta} filter (where {tempo} < {inicio}) as anterior"
                f" from {de} where {tempo} >= {inicio_anterior} group by 1"
            )
        except asyncpg.QueryCanceledError:
            raise Impossivel(SEM_TEMPO) from None
        for r in linhas:
            agora, antes = _numero(r["valor"]), _numero(r["anterior"])
            if agora is None and antes is None:
                continue
            fatores.append(
                {
                    "dimensao": dimensao,
                    "grupo": r["grupo"] or "sem valor",
                    "valor": agora,
                    "anterior": antes,
                    "diferenca": (agora or 0) - (antes or 0),
                    "variacao": variacao(agora, antes),
                }
            )
    return fatores
