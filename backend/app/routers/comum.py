import asyncio
import socket
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
    except OSError as e:
        raise HTTPException(502, _rede(e)) from None
    except ValueError as e:
        raise HTTPException(404, str(e)) from None
    except asyncpg.InterfaceError:
        raise HTTPException(
            502, "a conexão com o banco caiu no meio da leitura. Tente de novo."
        ) from None
    except asyncpg.PostgresError as e:
        raise HTTPException(502, _postgres(e)) from None


_FALHAS: dict[str, str] = {
    "28P01": "senha incorreta para o usuário informado",
    "28000": "o usuário informado não tem permissão de entrada nesse banco",
    "3D000": "o banco informado não existe nesse servidor",
    "42501": "o usuário informado não tem permissão para ler esse banco",
    "53300": "o banco recusou a conexão por estar com o número de conexões no limite",
    "3F000": "o schema informado não existe nesse banco",
    "42P01": "a tabela informada não existe nesse banco",
    "42P07": "a tabela informada já existe nesse banco",
    "0A000": "o servidor recusou a conexão por um recurso que não suporta",
}

_FRASES: tuple[tuple[str, str], ...] = (
    ("password authentication failed", "senha incorreta para o usuário informado"),
    (
        "no pg_hba.conf entry",
        "o servidor não aceita conexão deste host para este usuário",
    ),
    ('role "', "o usuário informado não existe nesse banco"),
    ('database "', "o banco informado não existe nesse servidor"),
    ("ssl", "o servidor exige SSL e a conexão não negociou"),
    ("timeout", "o banco não respondeu a tempo"),
    ("refused", "o host recusou a conexão, confira host e porta"),
)


def _postgres(e: asyncpg.PostgresError) -> str:
    sqlstate = getattr(e, "sqlstate", None) or ""
    baixo = str(e).lower()
    if sqlstate in _FALHAS:
        return f"Não foi possível conectar: {_FALHAS[sqlstate]}. Confira os dados."
    for marca, texto in _FRASES:
        if marca in baixo:
            return f"Não foi possível conectar: {texto}. Confira os dados."
    return "Não foi possível conectar ao banco. Confira host, porta e credenciais."


def _rede(e: OSError) -> str:
    if isinstance(e, socket.gaierror):
        return "Não foi possível resolver o host. Confira o endereço ou a DNS."
    if isinstance(e, ConnectionRefusedError):
        return "O host recusou a conexão. Confira o host e a porta."
    return "Não foi possível alcançar o host informado. Confira o endereço e a porta."


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
