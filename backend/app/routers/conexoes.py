from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from ..auth import CurrentUser
from ..cripto import cifrar
from ..db import Sessao
from ..introspeccao import listar_relacoes
from ..models import Conexao as ConexaoDb
from ..models import Indicador as IndicadorDb
from ..permissoes import exigir_dono, papel
from ..schemas import Conexao, ConexaoEtapa, ConexaoIn, Verificacao
from .comum import PREFIXO, buscar, consultar

router = APIRouter(prefix=PREFIXO, tags=["conexões"])


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


@router.post("/{conexao_id}/verificar", response_model=Verificacao)
async def verificar(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await buscar(sessao, organizacao_id, conexao_id)

    relacoes: list[dict] = []
    erro: str | None = None
    try:
        relacoes = await consultar(conexao, listar_relacoes)
    except HTTPException as e:
        erro = e.detail

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
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    if body.etapa == "pronta":
        tem = await sessao.scalar(
            select(IndicadorDb.id).where(IndicadorDb.conexao_id == conexao_id).limit(1)
        )
        if not tem:
            raise HTTPException(409, "defina ao menos um indicador antes de concluir")
    for campo, valor in body.model_dump(exclude_none=True).items():
        setattr(conexao, campo, valor)
    await sessao.flush()
    await sessao.refresh(conexao)
    resposta = Conexao.model_validate(conexao)
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
