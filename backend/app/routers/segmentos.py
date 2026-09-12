from fastapi import APIRouter
from sqlalchemy import select

from ..auth import CurrentUser
from ..db import Sessao
from ..models import Segmento as SegmentoDb
from ..schemas import Segmento

router = APIRouter(prefix="/segmentos", tags=["segmentos"])


@router.get("", response_model=list[Segmento])
async def listar(user: CurrentUser, sessao: Sessao):
    linhas = await sessao.scalars(select(SegmentoDb).order_by(SegmentoDb.ordem))
    return list(linhas)
