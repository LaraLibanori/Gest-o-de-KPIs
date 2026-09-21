import logging
import time

import asyncpg

from .introspeccao import citar, partir, qualificar

registro = logging.getLogger("kpi")

LIMITE_QUEBRA = 12
TEMPO_CONSULTA = 4000
# 8s de conexao mais isto cabem nos 15s que o navegador espera.
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
SEM_TEMPO = "o banco demorou demais, atualize para tentar de novo"


def _conta(indicador) -> str:
    return AGREGACOES[indicador.agregacao].format(citar(indicador.coluna or ""))


def _recorte(indicador) -> str:
    if not indicador.tempo or indicador.periodo not in RECORTES:
        return ""
    return f" where {citar(indicador.tempo)} >= {RECORTES[indicador.periodo]}"


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


async def _um(conexao: asyncpg.Connection, tabela: str, indicador) -> dict:
    if indicador.agregacao != "contagem" and not indicador.coluna:
        return {"erro": SEM_CAMPO}

    de = qualificar(*partir(tabela))
    onde = _recorte(indicador)
    valor = await conexao.fetchval(f"select {_conta(indicador)} from {de}{onde}")

    # Quebra que falha nao leva junto o numero que ja veio.
    try:
        linhas = await _serie(conexao, de, onde, indicador)
    except asyncpg.PostgresError:
        linhas = []
    return {"valor": _numero(valor), "linhas": linhas}


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
    resultados = {}
    for indicador in indicadores:
        if time.monotonic() > prazo:
            resultados[str(indicador.id)] = {"erro": SEM_TEMPO}
            continue
        try:
            resultados[str(indicador.id)] = await _um(conexao, tabela, indicador)
        except asyncpg.UndefinedColumnError:
            resultados[str(indicador.id)] = {"erro": SEM_COLUNA}
        except asyncpg.PostgresError as e:
            resultados[str(indicador.id)] = {"erro": str(e).split("\n")[0]}
        except Exception:  # noqa: BLE001 - um indicador nao derruba o painel
            registro.exception("falha ao calcular %s", indicador.nome)
            resultados[str(indicador.id)] = {"erro": "não foi possível calcular"}
    return resultados
