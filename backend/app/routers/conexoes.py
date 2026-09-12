import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from ..auth import CurrentUser
from ..cripto import cifrar, decifrar
from ..db import Sessao
from ..indicadores import PAPEIS_ACEITOS, QUANTOS, casar, por_regra
from ..introspeccao import ler_catalogo, listar_relacoes
from ..llm import sugerir
from ..models import Campo as CampoDb
from ..models import Conexao as ConexaoDb
from ..models import Indicador as IndicadorDb
from ..models import SegmentoKpi as KpiDb
from ..permissoes import exigir_dono, papel
from ..rede import RedeInterna, conferir
from ..schemas import (
    Campo,
    CampoIn,
    Conexao,
    ConexaoEtapa,
    ConexaoIn,
    Indicador,
    IndicadorEdicao,
    IndicadorIn,
    Proposta,
    Sugestao,
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


# Abre o banco da empresa, roda a tarefa e fecha, traduzindo a falha em HTTP.
async def _consultar(conexao: ConexaoDb, tarefa: Callable[[asyncpg.Connection], Any]):
    try:
        externa = await _abrir(conexao)
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
        relacoes = await _consultar(conexao, listar_relacoes)
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

    campos = await _consultar(
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


# Sugestao de rotulo e papel. So mexe no que o usuario ainda nao confirmou.
@router.post("/{conexao_id}/catalogo/rotulos", response_model=Sugestao)
async def sugerir_rotulos(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "sugerir rótulos")
    conexao = await _buscar(sessao, organizacao_id, conexao_id)
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


async def _campos(sessao, conexao_id: UUID) -> list[CampoDb]:
    return list(
        await sessao.scalars(
            select(CampoDb)
            .where(CampoDb.conexao_id == conexao_id)
            .order_by(CampoDb.ordem)
        )
    )


def _conferir(dados, campos: list[CampoDb], agregacao: str) -> None:
    por_nome = {c.coluna: c for c in campos}
    exigidos = [
        (dados.coluna, PAPEIS_ACEITOS[agregacao]),
        (dados.dimensao, ("dimensao",)),
        (dados.tempo, ("tempo",)),
    ]
    for coluna, aceitos in exigidos:
        if coluna is None:
            continue
        campo = por_nome.get(coluna)
        if campo is None:
            raise HTTPException(422, f"a coluna {coluna} não está no catálogo")
        if aceitos and campo.papel not in aceitos:
            raise HTTPException(422, f"{coluna} não serve para esse cálculo")


@router.get("/{conexao_id}/indicadores", response_model=list[Indicador])
async def listar_indicadores(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    await _buscar(sessao, organizacao_id, conexao_id)
    linhas = await sessao.scalars(
        select(IndicadorDb)
        .where(IndicadorDb.conexao_id == conexao_id)
        .order_by(IndicadorDb.ordem)
    )
    return list(linhas)


# Usa os indicadores do segmento e completa com regra ate fechar a conta.
@router.post("/{conexao_id}/indicadores/propor", response_model=Proposta)
async def propor(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "propor indicadores")
    conexao = await _buscar(sessao, organizacao_id, conexao_id)
    campos = await _campos(sessao, conexao_id)
    if not campos:
        raise HTTPException(409, "monte o catálogo antes")

    guardados = list(
        await sessao.scalars(
            select(IndicadorDb).where(IndicadorDb.conexao_id == conexao_id)
        )
    )
    mantidos = [i for i in guardados if i.confirmado]
    for i in guardados:
        if not i.confirmado:
            await sessao.delete(i)

    tempos = [c for c in campos if c.papel == "tempo"]
    tempo = tempos[0].coluna if tempos else None
    usados = {i.nome for i in mantidos}
    novos: list[dict] = []
    descartados: list[dict] = []

    if conexao.segmento:
        kpis = await sessao.scalars(
            select(KpiDb)
            .where(KpiDb.segmento == conexao.segmento)
            .order_by(KpiDb.ordem)
        )
        for kpi in kpis:
            resultado = casar(kpi, campos)
            if resultado["situacao"] == "impossivel":
                descartados.append(
                    {
                        "nome": kpi.nome,
                        "motivo": "a tabela não tem coluna que sirva para esse cálculo",
                    }
                )
                continue
            if kpi.nome in usados:
                continue
            usados.add(kpi.nome)
            novos.append(
                {
                    "nome": kpi.nome,
                    "agregacao": kpi.agregacao,
                    "coluna": resultado["coluna"],
                    "dimensao": None,
                    "tempo": tempo,
                    "periodo": "sempre",
                    "origem": "segmento",
                }
            )

    for bruto in por_regra(campos, QUANTOS + len(descartados)):
        if len(mantidos) + len(novos) >= QUANTOS:
            break
        if bruto["nome"] in usados:
            continue
        usados.add(bruto["nome"])
        novos.append({k: v for k, v in bruto.items() if k != "ordem"})

    ordem = len(mantidos)
    for dados in novos:
        ordem += 1
        sessao.add(IndicadorDb(conexao_id=conexao_id, ordem=ordem, **dados))

    conexao.etapa = "indicadores"
    await sessao.flush()
    linhas = await sessao.scalars(
        select(IndicadorDb)
        .where(IndicadorDb.conexao_id == conexao_id)
        .order_by(IndicadorDb.ordem)
    )
    resposta = Proposta(
        segmento=conexao.segmento,
        indicadores=[Indicador.model_validate(i) for i in linhas],
        descartados=descartados,
    )
    await sessao.commit()
    return resposta


@router.post("/{conexao_id}/indicadores", response_model=Indicador, status_code=201)
async def criar_indicador(
    organizacao_id: UUID,
    conexao_id: UUID,
    body: IndicadorIn,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "criar indicador")
    await _buscar(sessao, organizacao_id, conexao_id)
    campos = await _campos(sessao, conexao_id)
    _conferir(body, campos, body.agregacao)

    repetido = await sessao.scalar(
        select(IndicadorDb.id).where(
            IndicadorDb.conexao_id == conexao_id, IndicadorDb.nome == body.nome
        )
    )
    if repetido:
        raise HTTPException(409, "já existe um indicador com esse nome")

    ultima = await sessao.scalar(
        select(func.max(IndicadorDb.ordem)).where(IndicadorDb.conexao_id == conexao_id)
    )
    novo = IndicadorDb(
        conexao_id=conexao_id,
        origem="manual",
        confirmado=True,
        ordem=(ultima or 0) + 1,
        **body.model_dump(),
    )
    sessao.add(novo)
    await sessao.flush()
    await sessao.refresh(novo)
    resposta = Indicador.model_validate(novo)
    await sessao.commit()
    return resposta


@router.patch("/{conexao_id}/indicadores/{indicador_id}", response_model=Indicador)
async def ajustar_indicador(
    organizacao_id: UUID,
    conexao_id: UUID,
    indicador_id: UUID,
    body: IndicadorEdicao,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "ajustar indicador")
    await _buscar(sessao, organizacao_id, conexao_id)
    indicador = await sessao.scalar(
        select(IndicadorDb).where(
            IndicadorDb.id == indicador_id, IndicadorDb.conexao_id == conexao_id
        )
    )
    if indicador is None:
        raise HTTPException(404, "indicador não encontrado")

    mudancas = body.model_dump(exclude_unset=True)
    for nome, valor in mudancas.items():
        setattr(indicador, nome, valor)
    _conferir(indicador, await _campos(sessao, conexao_id), indicador.agregacao)

    await sessao.flush()
    await sessao.refresh(indicador)
    resposta = Indicador.model_validate(indicador)
    await sessao.commit()
    return resposta


@router.delete("/{conexao_id}/indicadores/{indicador_id}", status_code=204)
async def remover_indicador(
    organizacao_id: UUID,
    conexao_id: UUID,
    indicador_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "apagar indicador")
    resultado = await sessao.execute(
        delete(IndicadorDb).where(
            IndicadorDb.id == indicador_id, IndicadorDb.conexao_id == conexao_id
        )
    )
    if resultado.rowcount == 0:
        raise HTTPException(404, "indicador não encontrado")
    await sessao.commit()
