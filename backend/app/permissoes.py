from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Membro


async def papel(sessao: AsyncSession, organizacao_id: UUID, usuario_id: UUID) -> str:
    resultado = await sessao.scalar(
        select(Membro.papel).where(
            Membro.organizacao_id == organizacao_id,
            Membro.usuario_id == usuario_id,
        )
    )
    # 404 e nao 403: quem nao participa nem fica sabendo que a organizacao existe.
    if resultado is None:
        raise HTTPException(404, "organização não encontrada")
    return resultado


async def exigir_dono(
    sessao: AsyncSession, organizacao_id: UUID, usuario_id: UUID, acao: str
) -> None:
    if await papel(sessao, organizacao_id, usuario_id) != "dono":
        raise HTTPException(403, f"só o dono pode {acao}")
