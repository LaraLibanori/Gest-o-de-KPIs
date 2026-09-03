from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..auth import CurrentUser
from ..db import get_pool
from ..schemas import Indicador, IndicadorIn, Valor
from ..sources import validar

router = APIRouter(tags=["indicadores"])


async def _dashboard_do_usuario(pool, dashboard_id: UUID, user_id: str) -> None:
    dono = await pool.fetchval(
        "select 1 from dashboards where id = $1 and owner_id = $2::uuid",
        dashboard_id,
        user_id,
    )
    if not dono:
        raise HTTPException(404, "dashboard não encontrado")


@router.get("/dashboards/{dashboard_id}/indicadores", response_model=list[Indicador])
async def listar(dashboard_id: UUID, user: CurrentUser):
    pool = await get_pool()
    await _dashboard_do_usuario(pool, dashboard_id, user.id)
    rows = await pool.fetch(
        "select id, dashboard_id, nome, fonte, coluna, agregacao from indicadores"
        " where dashboard_id = $1 order by criado_em",
        dashboard_id,
    )
    return [dict(r) for r in rows]


@router.post(
    "/dashboards/{dashboard_id}/indicadores", response_model=Indicador, status_code=201
)
async def criar(dashboard_id: UUID, body: IndicadorIn, user: CurrentUser):
    try:
        validar(body.fonte, body.coluna, body.agregacao)
    except ValueError as e:
        raise HTTPException(422, str(e))

    pool = await get_pool()
    await _dashboard_do_usuario(pool, dashboard_id, user.id)
    row = await pool.fetchrow(
        "insert into indicadores (dashboard_id, nome, fonte, coluna, agregacao)"
        " values ($1, $2, $3, $4, $5)"
        " returning id, dashboard_id, nome, fonte, coluna, agregacao",
        dashboard_id,
        body.nome,
        body.fonte,
        body.coluna,
        body.agregacao,
    )
    return dict(row)


@router.get("/indicadores/{indicador_id}/valor", response_model=Valor)
async def calcular(indicador_id: UUID, user: CurrentUser):
    pool = await get_pool()
    ind = await pool.fetchrow(
        "select i.id, i.nome, i.fonte, i.coluna, i.agregacao from indicadores i"
        " join dashboards d on d.id = i.dashboard_id"
        " where i.id = $1 and d.owner_id = $2::uuid",
        indicador_id,
        user.id,
    )
    if ind is None:
        raise HTTPException(404, "indicador não encontrado")

    # Confere de novo: a lista de fontes pode ter mudado depois de salvar.
    try:
        validar(ind["fonte"], ind["coluna"], ind["agregacao"])
    except ValueError as e:
        raise HTTPException(422, str(e))

    alvo = "*" if ind["agregacao"] == "count" else ind["coluna"]
    sql = (
        f'select {ind["agregacao"]}({alvo}) from {ind["fonte"]}'
        " where owner_id = $1::uuid"
    )
    valor = await pool.fetchval(sql, user.id)
    return Valor(
        indicador_id=ind["id"],
        nome=ind["nome"],
        valor=None if valor is None else float(valor),
    )


@router.delete("/indicadores/{indicador_id}", status_code=204)
async def remover(indicador_id: UUID, user: CurrentUser):
    pool = await get_pool()
    result = await pool.execute(
        "delete from indicadores i using dashboards d"
        " where i.dashboard_id = d.id and i.id = $1 and d.owner_id = $2::uuid",
        indicador_id,
        user.id,
    )
    if result == "DELETE 0":
        raise HTTPException(404, "indicador não encontrado")
