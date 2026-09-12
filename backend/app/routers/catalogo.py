from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from ..auth import CurrentUser
from ..db import Sessao
from ..introspeccao import ler_catalogo
from ..llm import sugerir
from ..models import Campo as CampoDb
from ..permissoes import exigir_dono, papel
from ..schemas import Campo, CampoIn, Sugestao
from .comum import PREFIXO, buscar, consultar

router = APIRouter(prefix=PREFIXO, tags=["catálogo"])


@router.get("/{conexao_id}/catalogo", response_model=list[Campo])
async def listar_catalogo(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    await buscar(sessao, organizacao_id, conexao_id)
    linhas = await sessao.scalars(
        select(CampoDb).where(CampoDb.conexao_id == conexao_id).order_by(CampoDb.ordem)
    )
    return list(linhas)


@router.post("/{conexao_id}/catalogo", response_model=list[Campo], status_code=201)
async def montar_catalogo(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "montar o catálogo")
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    if not conexao.tabela_fato:
        raise HTTPException(409, "escolha a tabela fato antes")

    campos = await consultar(
        conexao, lambda externa: ler_catalogo(externa, conexao.tabela_fato)
    )

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


@router.post("/{conexao_id}/catalogo/rotulos", response_model=Sugestao)
async def sugerir_rotulos(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "sugerir rótulos")
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    campos = list(
        await sessao.scalars(
            select(CampoDb)
            .where(CampoDb.conexao_id == conexao_id)
            .order_by(CampoDb.ordem)
        )
    )

    sugestoes = await sugerir(
        [
            {"coluna": c.coluna, "tipo": c.tipo, "cardinalidade": c.cardinalidade}
            for c in campos
        ],
        conexao.tabela_fato or "",
        conexao.descricao_negocio,
    )

    aplicadas = 0
    for campo in campos:
        sugestao = sugestoes.get(campo.coluna)
        if not sugestao or campo.confirmado:
            continue
        campo.rotulo = sugestao.rotulo
        campo.papel = sugestao.papel
        aplicadas += 1

    await sessao.flush()
    resposta = Sugestao(
        aplicadas=aplicadas, campos=[Campo.model_validate(c) for c in campos]
    )
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
    await buscar(sessao, organizacao_id, conexao_id)
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
