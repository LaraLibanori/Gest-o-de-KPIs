from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..auth import CurrentUser
from ..db import Sessao
from ..models import Perfil as PerfilDb
from ..schemas import Perfil

router = APIRouter(tags=["perfil"])


@router.get("/perfil", response_model=Perfil)
async def meu_perfil(user: CurrentUser, sessao: Sessao):
    perfil = await sessao.scalar(select(PerfilDb).where(PerfilDb.id == user.id))
    if perfil is None:
        raise HTTPException(404, "perfil não encontrado")
    return perfil
