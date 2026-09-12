import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .auth import CurrentUser
from .config import DATABASE_URL, USAR_POOL, url_asyncpg

_fabrica: async_sessionmaker[AsyncSession] | None = None


# Guardar conexao so vale em processo longo, com um event loop so.
def _pool() -> dict:
    if USAR_POOL:
        return {"pool_size": 5, "max_overflow": 0, "pool_recycle": 280}
    return {"poolclass": NullPool}


def _sessoes() -> async_sessionmaker[AsyncSession]:
    global _fabrica
    if _fabrica is None:
        # Nome unico por statement, senao dois clientes colidem no pooler.
        motor = create_async_engine(
            url_asyncpg(DATABASE_URL),
            **_pool(),
            connect_args={
                "statement_cache_size": 0,
                "command_timeout": 10,
                "prepared_statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__kpi_{uuid4().hex}__",
            },
        )
        _fabrica = async_sessionmaker(motor, expire_on_commit=False)
    return _fabrica


async def abrir_sessao(user: CurrentUser) -> AsyncIterator[AsyncSession]:
    async with _sessoes()() as sessao:
        # O true prende o valor a transacao: senao vaza para o proximo cliente.
        await sessao.execute(
            text("select set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps({"sub": str(user.id), "role": "authenticated"})},
        )
        yield sessao


Sessao = Annotated[AsyncSession, Depends(abrir_sessao)]


def abrir_conexao():
    return _sessoes()()
