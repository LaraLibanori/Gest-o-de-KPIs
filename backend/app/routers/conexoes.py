import asyncio
from datetime import datetime, timezone
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from ..auth import CurrentUser
from ..cripto import cifrar, decifrar
from ..db import Sessao
from ..introspeccao import ler_catalogo, listar_relacoes
from ..models import Campo as CampoDb
from ..models import Conexao as ConexaoDb
from ..permissoes import exigir_dono, papel
from ..rede import RedeInterna, conferir
from ..schemas import (
    Campo,
    CampoIn,
    Conexao,
    ConexaoEtapa,
    ConexaoIn,
    Verificacao,
)

router = APIRouter(prefix="/organizacoes/{organizacao_id}/conexoes", tags=["conexões"])

TEMPO_LIMITE = 8


async def _abrir(conexao: ConexaoDb) -> asyncpg.Connection:
    await conferir(conexao.host)
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
        etapa="tabela",
        criada_por=user.id,
    )
    sessao.add(nova)
    await sessao.flush()
    await sessao.refresh(nova)
    resposta = Conexao.model_validate(nova)
    await sessao.commit()
    return resposta


# Abre o banco da empresa de verdade e guarda o resultado, para o cartao da
# conexao poder dizer se ela responde.
@router.post("/{conexao_id}/verificar", response_model=Verificacao)
async def verificar(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await _buscar(sessao, organizacao_id, conexao_id)

    relacoes: list[dict] = []
    erro: str | None = None
    try:
        externa = await _abrir(conexao)
        try:
            relacoes = await listar_relacoes(externa)
        finally:
            await externa.close()
    except RedeInterna as e:
        erro = str(e)
    except TimeoutError:
        erro = f"o banco não respondeu em {TEMPO_LIMITE} segundos"
    except OSError:
        erro = "não foi possível alcançar o host informado"
    except asyncpg.PostgresError as e:
        erro = str(e)

    conexao.verificada_em = datetime.now(timezone.utc)
    conexao.verificacao_erro = erro
    await sessao.commit()
    return Verificacao(ok=erro is None, erro=erro, relacoes=relacoes)


@router.patch("/{conexao_id}", response_model=Conexao)
async def avancar(
    organizacao_id: UUID,
    conexao_id: UUID,
    body: ConexaoEtapa,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "editar conexão")
    conexao = await _buscar(sessao, organizacao_id, conexao_id)
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(conexao, campo, valor)
    await sessao.flush()
    await sessao.refresh(conexao)
    resposta = Conexao.model_validate(conexao)
    await sessao.commit()
    return resposta


@router.get("/{conexao_id}/catalogo", response_model=list[Campo])
async def listar_catalogo(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    await _buscar(sessao, organizacao_id, conexao_id)
    linhas = await sessao.scalars(
        select(CampoDb).where(CampoDb.conexao_id == conexao_id).order_by(CampoDb.ordem)
    )
    return list(linhas)


# Le as colunas da tabela fato e classifica por tipo e cardinalidade.
@router.post("/{conexao_id}/catalogo", response_model=list[Campo], status_code=201)
async def montar_catalogo(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "montar o catálogo")
    conexao = await _buscar(sessao, organizacao_id, conexao_id)
    if not conexao.tabela_fato:
        raise HTTPException(409, "escolha a tabela fato antes")

    try:
        externa = await _abrir(conexao)
        try:
            campos = await ler_catalogo(externa, conexao.tabela_fato)
        finally:
            await externa.close()
    except RedeInterna as e:
        raise HTTPException(400, str(e)) from None
    except TimeoutError:
        raise HTTPException(504, "o banco não respondeu a tempo") from None
    except OSError:
        raise HTTPException(502, "não foi possível alcançar o host") from None
    except ValueError as e:
        raise HTTPException(404, str(e)) from None
    except asyncpg.PostgresError as e:
        raise HTTPException(502, str(e)) from None

    await sessao.execute(delete(CampoDb).where(CampoDb.conexao_id == conexao_id))
    sessao.add_all([CampoDb(conexao_id=conexao_id, **c) for c in campos])
    conexao.etapa = "catalogo"
    await sessao.flush()
    linhas = await sessao.scalars(
        select(CampoDb).where(CampoDb.conexao_id == conexao_id).order_by(CampoDb.ordem)
    )
    resposta = [Campo.model_validate(c) for c in linhas]
    await sessao.commit()
    return resposta


@router.patch("/{conexao_id}/catalogo/{campo_id}", response_model=Campo)
async def ajustar_campo(
    organizacao_id: UUID,
    conexao_id: UUID,
    campo_id: UUID,
    body: CampoIn,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "ajustar o catálogo")
    await _buscar(sessao, organizacao_id, conexao_id)
    campo = await sessao.scalar(
        select(CampoDb).where(CampoDb.id == campo_id, CampoDb.conexao_id == conexao_id)
    )
    if campo is None:
        raise HTTPException(404, "campo não encontrado")
    for nome, valor in body.model_dump(exclude_none=True).items():
        setattr(campo, nome, valor)
    await sessao.flush()
    await sessao.refresh(campo)
    resposta = Campo.model_validate(campo)
    await sessao.commit()
    return resposta


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
