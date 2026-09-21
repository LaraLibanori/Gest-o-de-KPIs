import logging
import time

import asyncpg

from .introspeccao import citar, partir, qualificar

registro = logging.getLogger("kpi")

LIMITE_QUEBRA = 12
TEMPO_CONSULTA = 4000
# Teto do calculo em si; o navegador desiste da pagina em 15s.
ORCAMENTO = 6

AGREGACOES = {
    "soma": "sum({})",
    "media": "avg({})",
    "contagem": "count(*)",
    "distintos": "count(distinct {})",
    "minimo": "min({})",
    "maximo": "max({})",
}

# Fragmentos fixos: o periodo vem de lista fechada, nunca de texto do usuario.
RECORTES = {
    "ultimos_7_dias": "current_date - 7",
    "ultimos_30_dias": "current_date - 30",
    "ultimos_90_dias": "current_date - 90",
    "ano_atual": "date_trunc('year', current_date)",
}

# O balde acompanha a janela: semana curta vira dia, ano vira mes.
BALDES = {
    "ultimos_7_dias": "day",
    "ultimos_30_dias": "day",
    "ultimos_90_dias": "week",
}
BALDE_LARGO = "month"
LIMITE_SERIE = 200

SEM_CAMPO = "escolha o campo do indicador"
SEM_COLUNA = "a coluna não existe mais na tabela"
SEM_NUMERO = "a coluna não guarda número"
SEM_TEMPO = "o banco demorou demais, atualize para tentar de novo"
CAIU = "a conexão com o banco caiu"


def _conta(indicador) -> str:
    return AGREGACOES[indicador.agregacao].format(citar(indicador.coluna or ""))


def _recorte(indicador) -> str:
    if not indicador.tempo or indicador.periodo not in RECORTES:
        return ""
    return f" where {citar(indicador.tempo)} >= {RECORTES[indicador.periodo]}"


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


# Texto onde se esperava numero e problema de um indicador, nao do lote.
def _valor(bruto) -> dict:
    try:
        return {"valor": _numero(bruto), "linhas": []}
    except (TypeError, ValueError):
        return {"erro": SEM_NUMERO}


def _caiu(erro: Exception) -> bool:
    return isinstance(erro, asyncpg.PostgresConnectionError | asyncpg.InterfaceError)


def _falha(erro: Exception) -> dict:
    if isinstance(erro, asyncpg.UndefinedColumnError):
        return {"erro": SEM_COLUNA}
    if _caiu(erro):
        return {"erro": CAIU}
    if isinstance(erro, asyncpg.PostgresError):
        return {"erro": str(erro).split("\n")[0]}
    registro.exception("falha inesperada ao calcular")
    return {"erro": "não foi possível calcular"}


# Mesmo recorte cabe num select so; se ele falhar, refaz um por um para o erro
# ficar no indicador certo.
async def _valores(conexao, de: str, onde: str, grupo: list, prazo: float) -> dict:
    try:
        campos = ", ".join(f"{_conta(i)} as v{n}" for n, i in enumerate(grupo))
        linha = await conexao.fetchrow(f"select {campos} from {de}{onde}")
        return {str(i.id): _valor(linha[f"v{n}"]) for n, i in enumerate(grupo)}
    except Exception as e:  # noqa: BLE001 - o culpado aparece na segunda passada
        saida = {str(i.id): _falha(e) for i in grupo}
        if _caiu(e):
            return saida

    for indicador in grupo:
        if time.monotonic() > prazo:
            break
        try:
            bruto = await conexao.fetchval(
                f"select {_conta(indicador)} from {de}{onde}"
            )
            saida[str(indicador.id)] = _valor(bruto)
        except Exception as e:  # noqa: BLE001 - um indicador nao derruba o grupo
            saida[str(indicador.id)] = _falha(e)
            if _caiu(e):
                break
    return saida


async def _serie(conexao, de: str, onde: str, indicador) -> list[dict]:
    if indicador.grafico == "numero":
        return []
    if indicador.grafico == "linha" and indicador.tempo:
        balde = BALDES.get(indicador.periodo or "", BALDE_LARGO)
        sql = (
            f"select date_trunc('{balde}', {citar(indicador.tempo)})::date::text"
            f" as rotulo, {_conta(indicador)} as valor from {de}{onde}"
            f" group by 1 order by 1 limit {LIMITE_SERIE}"
        )
    elif indicador.dimensao:
        sql = (
            f"select {citar(indicador.dimensao)}::text as rotulo,"
            f" {_conta(indicador)} as valor from {de}{onde}"
            f" group by 1 order by 2 desc nulls last limit {LIMITE_QUEBRA}"
        )
    else:
        return []

    return [
        {"rotulo": r["rotulo"] or "sem valor", "valor": _numero(r["valor"])}
        for r in await conexao.fetch(sql)
    ]


# Uma conexao para todos: indicador que falha nao derruba os outros.
async def calcular(conexao: asyncpg.Connection, tabela: str, indicadores) -> dict:
    await conexao.execute(f"set statement_timeout = {TEMPO_CONSULTA}")
    prazo = time.monotonic() + ORCAMENTO
    de = qualificar(*partir(tabela))

    resultados: dict[str, dict] = {}
    grupos: dict[str, list] = {}
    for indicador in indicadores:
        if indicador.agregacao != "contagem" and not indicador.coluna:
            resultados[str(indicador.id)] = {"erro": SEM_CAMPO}
            continue
        grupos.setdefault(_recorte(indicador), []).append(indicador)

    for onde, grupo in grupos.items():
        if time.monotonic() > prazo:
            resultados.update({str(i.id): {"erro": SEM_TEMPO} for i in grupo})
            continue
        resultados.update(await _valores(conexao, de, onde, grupo, prazo))

    # A quebra vem depois: o numero ja esta na mao e o desenho e o que pode faltar.
    for indicador in indicadores:
        dados = resultados[str(indicador.id)]
        if "erro" in dados or time.monotonic() > prazo:
            continue
        try:
            dados["linhas"] = await _serie(conexao, de, _recorte(indicador), indicador)
        except Exception:  # noqa: BLE001 - sem a quebra o numero ainda serve
            registro.exception("falha na quebra de %s", indicador.nome)
    return resultados
