import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import HTTPException
from sqlalchemy import select

from ..cripto import decifrar
from ..models import Campo as CampoDb
from ..models import Conexao as ConexaoDb
from ..rede import RedeInterna, conferir

PREFIXO = "/organizacoes/{organizacao_id}/conexoes"

TEMPO_LIMITE = 8


async def abrir(conexao: ConexaoDb) -> asyncpg.Connection:
    endereco = await conferir(conexao.host)
    return await asyncio.wait_for(
        asyncpg.connect(
            host=endereco,
            port=conexao.porta,
            database=conexao.banco,
            user=conexao.usuario,
            password=decifrar(conexao.senha_cifrada),
            statement_cache_size=0,
        ),
        timeout=TEMPO_LIMITE,
    )


# Abre o banco da empresa, roda a tarefa e fecha, traduzindo a falha em HTTP.
async def consultar(conexao: ConexaoDb, tarefa: Callable[[asyncpg.Connection], Any]):
    try:
        externa = await abrir(conexao)
        try:
            return await tarefa(externa)
        finally:
            await externa.close()
    except RedeInterna as e:
        raise HTTPException(400, str(e)) from None
    except TimeoutError:
        raise HTTPException(
            504, f"o banco não respondeu em {TEMPO_LIMITE} segundos"
        ) from None
    except OSError:
        raise HTTPException(502, "não foi possível alcançar o host informado") from None
    except ValueError as e:
        raise HTTPException(404, str(e)) from None
    except asyncpg.PostgresError as e:
        raise HTTPException(502, str(e)) from None


async def buscar(sessao, organizacao_id: UUID, conexao_id: UUID) -> ConexaoDb:
    conexao = await sessao.scalar(
        select(ConexaoDb).where(
            ConexaoDb.id == conexao_id, ConexaoDb.organizacao_id == organizacao_id
        )
    )
    if conexao is None:
        raise HTTPException(404, "conexão não encontrada")
    return conexao


async def campos(sessao, conexao_id: UUID) -> list[CampoDb]:
    return list(
        await sessao.scalars(
            select(CampoDb)
            .where(CampoDb.conexao_id == conexao_id)
            .order_by(CampoDb.ordem)
        )
    )
