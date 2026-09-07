import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .auth import CurrentUser
from .config import DATABASE_URL, url_asyncpg

_fabrica: async_sessionmaker[AsyncSession] | None = None


def _sessoes() -> async_sessionmaker[AsyncSession]:
    global _fabrica
    if _fabrica is None:
        # Nome unico por statement, senao dois clientes colidem no pooler.
        motor = create_async_engine(
            url_asyncpg(DATABASE_URL),
            poolclass=NullPool,
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
        # E daqui que o auth.uid() das policies le o usuario. O terceiro
        # argumento true deixa o valor preso a transacao: sem isso ele sobraria
        # na conexao e vazaria para o proximo cliente do pooler.
        await sessao.execute(
            text("select set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps({"sub": str(user.id), "role": "authenticated"})},
        )
        yield sessao


Sessao = Annotated[AsyncSession, Depends(abrir_sessao)]


# Usado pelo /ready: erro de conexao aqui vira 503, e nao 500 na dependencia.
def abrir_conexao():
    return _sessoes()()
