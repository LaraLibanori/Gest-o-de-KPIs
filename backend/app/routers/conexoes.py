import asyncio
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from ..auth import CurrentUser
from ..cripto import cifrar, decifrar
from ..db import Sessao
from ..models import Conexao as ConexaoDb
from ..permissoes import exigir_dono, papel
from ..schemas import Conexao, ConexaoIn, Verificacao

router = APIRouter(prefix="/organizacoes/{organizacao_id}/conexoes", tags=["conexões"])

TEMPO_LIMITE = 8

TABELAS = """
    select table_name from information_schema.tables
    where table_schema = 'public' and table_type = 'BASE TABLE'
    order by table_name
"""


async def _abrir(conexao: ConexaoDb) -> asyncpg.Connection:
    return await asyncio.wait_for(
        asyncpg.connect(
            host=conexao.host,
            port=conexao.porta,
            database=conexao.banco,
            user=conexao.usuario,
            password=decifrar(conexao.senha_cifrada),
            statement_cache_size=0,
        ),
        timeout=TEMPO_LIMITE,
    )


async def _buscar(sessao, organizacao_id: UUID, conexao_id: UUID) -> ConexaoDb:
    conexao = await sessao.scalar(
        select(ConexaoDb).where(
            ConexaoDb.id == conexao_id, ConexaoDb.organizacao_id == organizacao_id
        )
    )
    if conexao is None:
        raise HTTPException(404, "conexão não encontrada")
    return conexao


@router.get("", response_model=list[Conexao])
async def listar(organizacao_id: UUID, user: CurrentUser, sessao: Sessao):
    await papel(sessao, organizacao_id, user.id)
    linhas = await sessao.scalars(
        select(ConexaoDb)
        .where(ConexaoDb.organizacao_id == organizacao_id)
        .order_by(ConexaoDb.criada_em.desc())
    )
    return list(linhas)


@router.post("", response_model=Conexao, status_code=201)
async def criar(
    organizacao_id: UUID, body: ConexaoIn, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "criar conexão")

    repetido = await sessao.scalar(
        select(ConexaoDb.id).where(
            ConexaoDb.organizacao_id == organizacao_id, ConexaoDb.nome == body.nome
        )
    )
    if repetido:
        raise HTTPException(409, "já existe uma conexão com esse nome")

    nova = ConexaoDb(
        organizacao_id=organizacao_id,
        nome=body.nome,
        host=body.host,
        porta=body.porta,
        banco=body.banco,
        usuario=body.usuario,
        senha_cifrada=cifrar(body.senha),
        tabela_fato=body.tabela_fato,
        criada_por=user.id,
    )
    sessao.add(nova)
    await sessao.flush()
    await sessao.refresh(nova)
    resposta = Conexao.model_validate(nova)
    await sessao.commit()
    return resposta


# Abre o banco da empresa de verdade e guarda o resultado, para o cartão da
# conexão poder dizer se ela responde.
@router.post("/{conexao_id}/verificar", response_model=Verificacao)
async def verificar(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await _buscar(sessao, organizacao_id, conexao_id)

    tabelas: list[str] = []
    erro: str | None = None
    try:
        externa = await _abrir(conexao)
        try:
            tabelas = [r["table_name"] for r in await externa.fetch(TABELAS)]
        finally:
            await externa.close()
    except TimeoutError:
        erro = f"o banco não respondeu em {TEMPO_LIMITE} segundos"
    except OSError:
        erro = "não foi possível alcançar o host informado"
    except asyncpg.PostgresError as e:
        erro = str(e)

    conexao.verificada_em = datetime.now(timezone.utc)
    conexao.verificacao_erro = erro
    await sessao.commit()
    return Verificacao(ok=erro is None, erro=erro, tabelas=tabelas)


@router.delete("/{conexao_id}", status_code=204)
async def remover(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "apagar conexão")
    resultado = await sessao.execute(
        delete(ConexaoDb).where(
            ConexaoDb.id == conexao_id, ConexaoDb.organizacao_id == organizacao_id
        )
    )
    if resultado.rowcount == 0:
        raise HTTPException(404, "conexão não encontrada")
    await sessao.commit()
