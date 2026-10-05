import os

from fastapi import HTTPException
from sqlalchemy import text

from .auth import CurrentUser
from .db import Sessao, entrar

POR_USUARIO = int(os.environ.get("LLM_LIMITE_USUARIO", "20"))
TOTAL = int(os.environ.get("LLM_LIMITE_TOTAL", "200"))

RECUSAS = {
    "usuario": "você atingiu o limite diário de sugestões automáticas. Tente amanhã.",
    "total": "o limite diário de sugestões automáticas do sistema foi atingido.",
}


async def reservar(sessao: Sessao, user: CurrentUser) -> None:
    resultado = await sessao.scalar(
        text("select public.reservar_llm(:u, :t)"), {"u": POR_USUARIO, "t": TOTAL}
    )
    # Grava a reserva antes da chamada lenta, senao uma falha a devolveria de graca.
    await sessao.commit()
    await entrar(sessao, user)
    if resultado != "ok":
        raise HTTPException(429, RECUSAS[resultado])
