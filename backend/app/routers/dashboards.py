from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..auth import CurrentUser
from ..db import get_pool
from ..schemas import Dashboard, DashboardIn

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("", response_model=list[Dashboard])
async def listar(user: CurrentUser):
    pool = await get_pool()
    rows = await pool.fetch(
        "select id, nome, criado_em from dashboards"
        " where owner_id = $1::uuid order by criado_em desc",
        user.id,
    )
    return [dict(r) for r in rows]


@router.post("", response_model=Dashboard, status_code=201)
async def criar(body: DashboardIn, user: CurrentUser):
    pool = await get_pool()
    row = await pool.fetchrow(
        "insert into dashboards (owner_id, nome) values ($1::uuid, $2)"
        " returning id, nome, criado_em",
        user.id,
        body.nome,
    )
    return dict(row)


@router.delete("/{dashboard_id}", status_code=204)
async def remover(dashboard_id: UUID, user: CurrentUser):
    pool = await get_pool()
    result = await pool.execute(
        "delete from dashboards where id = $1::uuid and owner_id = $2::uuid",
        dashboard_id,
        user.id,
    )
    if result == "DELETE 0":
        raise HTTPException(404, "dashboard não encontrado")
