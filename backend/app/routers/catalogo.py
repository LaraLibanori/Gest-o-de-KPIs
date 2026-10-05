from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from ..auth import CurrentUser
from ..db import Sessao
from ..introspeccao import ler_catalogo
from ..llm import sugerir
from ..models import Campo as CampoDb
from ..permissoes import exigir_dono, papel
from ..schemas import Campo, CampoIn, Sugestao
from .comum import PREFIXO, buscar, consultar
from .comum import campos as campos_da

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

    campos_lidos = await consultar(
        conexao, lambda externa: ler_catalogo(externa, conexao.tabela_fato)
    )

    atuais = {c.coluna: c for c in await campos_da(sessao, conexao_id)}
    lidas = {c["coluna"] for c in campos_lidos}
    for coluna, campo in atuais.items():
        if not campo.formula and coluna not in lidas:
            await sessao.delete(campo)
    for c in campos_lidos:
        campo = atuais.get(c["coluna"])
        if campo is None:
            sessao.add(CampoDb(conexao_id=conexao_id, papel_regra=c["papel"], **c))
            continue
        campo.tipo = c["tipo"]
        campo.cardinalidade = c["cardinalidade"]
        campo.papel_regra = c["papel"]
        campo.ordem = c["ordem"]
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
    campos = await campos_da(sessao, conexao_id)

    sugestoes = await sugerir(
        [
            {"coluna": c.coluna, "tipo": c.tipo, "cardinalidade": c.cardinalidade}
            for c in campos
            if not c.formula
        ],
        conexao.tabela_fato or "",
        conexao.descricao_negocio,
    )

    # A llm demora; relê para não sobrescrever o que foi confirmado nesse meio tempo.
    campos = list(
        await sessao.scalars(
            select(CampoDb)
            .where(CampoDb.conexao_id == conexao_id)
            .order_by(CampoDb.ordem)
            .execution_options(populate_existing=True)
        )
    )
    aplicadas = 0
    for campo in campos:
        sugestao = sugestoes.get(campo.coluna)
        if not sugestao or campo.formula:
            continue
        campo.papel_modelo = sugestao.papel
        if campo.confirmado:
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


@router.post("/{conexao_id}/catalogo/confirmar", response_model=list[Campo])
async def confirmar_catalogo(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "confirmar o catálogo")
    await buscar(sessao, organizacao_id, conexao_id)
    await sessao.execute(
        update(CampoDb)
        .where(CampoDb.conexao_id == conexao_id, CampoDb.formula.is_(None))
        .values(confirmado=True)
    )
    resposta = [Campo.model_validate(c) for c in await campos_da(sessao, conexao_id)]
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
