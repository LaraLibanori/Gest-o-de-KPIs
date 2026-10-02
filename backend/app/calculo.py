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

# Inicio de agora, inicio da janela anterior e balde da serie; fragmentos fixos.
JANELAS: dict[str, tuple[str, str, str]] = {
    "7d": ("current_date - 7", "current_date - 14", "day"),
    "30d": ("current_date - 30", "current_date - 60", "day"),
    "90d": ("current_date - 90", "current_date - 180", "week"),
    "12m": ("current_date - 365", "current_date - 730", "month"),
    "tudo": ("", "", "month"),
}
JANELA_PADRAO = "30d"
LIMITE_SERIE = 400

SEM_CAMPO = "escolha o campo do indicador"
SEM_COLUNA = "a coluna não existe mais na tabela"
SEM_NUMERO = "a coluna não guarda número"
SEM_TEMPO = "o banco demorou demais, atualize para tentar de novo"
CAIU = "a conexão com o banco caiu"


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
    return None if valor is None else float(valor)


def variacao(agora: float | None, antes: float | None) -> float | None:
    # Base zero nao tem variacao: dividir por zero e dizer "infinito" e mentira.
    if agora is None or not antes:
        return None
    return (agora - antes) / abs(antes) * 100


def _caiu(erro: Exception) -> bool:
    return isinstance(erro, asyncpg.PostgresConnectionError | asyncpg.InterfaceError)


# Um nivel de subquery por campo, porque alias nao vale no mesmo select.
def _fonte(tabela: str, calculados: list[tuple[str, str]] | None) -> str:
    if not calculados:
        return qualificar(*partir(tabela))
    base = qualificar(*partir(tabela))
    fonte = base
    for nome, formula in calculados:
        fonte = f"(select *, ({formula}) as {citar(nome)} from {fonte}) as c"
    return fonte


def _falha(erro: Exception) -> dict:
    if isinstance(erro, asyncpg.UndefinedColumnError):
        return {"erro": SEM_COLUNA}
    if _caiu(erro):
        return {"erro": CAIU}
    if isinstance(erro, asyncpg.PostgresError):
        return {"erro": str(erro).split("\n")[0]}
    registro.exception("falha inesperada ao calcular")
    return {"erro": "não foi possível calcular"}


# Sem where externo: o filtro de agregacao roda sobre o que sobrou do where.
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
        if _caiu(e):
            return {str(i.id): _falha(e) for i in grupo}
        saida: dict[str, dict] = {}
        for indicador in grupo:
            try:
                # Onde_atual ja vem com o " where"; repetir viraria syntax error.
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
        except (TypeError, ValueError):
            saida[str(indicador.id)] = {"erro": SEM_NUMERO}
            continue
        antes_ = _numero(linha[f"a{n}"]) if antes else None
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
    tempo = com_tempo[0].tempo if com_tempo else None

    if time.monotonic() > prazo:
        return {**resultados, **{str(i.id): {"erro": SEM_TEMPO} for i in validos}}

    if com_tempo:
        atual = _filtro(tempo, inicio)
        antes = (
            _filtro(tempo, inicio_anterior, f" and {citar(tempo)} < {inicio}")
            if inicio_anterior
            else ""
        )
        resultados.update(
            await _valores(conexao, de, atual, antes, com_tempo, _onde(tempo, inicio))
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
            dados["serie"] = await _serie(
                conexao, de, _onde(tempo, inicio), tempo, balde, _conta(indicador)
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
) -> list[dict]:
    inicio, _, _ = janela_de(janela)
    tempo = indicador.tempo if indicador.tempo else None
    onde = _onde(tempo, inicio)
    return [
        {"rotulo": r["rotulo"] or "sem valor", "valor": _numero(r["valor"])}
        for r in await conexao.fetch(
            f"select {citar(dimensao)}::text as rotulo, {_conta(indicador)} as valor"
            f" from {_fonte(tabela, calculados)}{onde} group by 1"
            f" order by 2 desc nulls last limit {int(limite)}",
        )
    ]
