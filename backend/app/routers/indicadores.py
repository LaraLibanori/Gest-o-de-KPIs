from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from ..auth import CurrentUser
from ..db import Sessao
from ..indicadores import PAPEIS_ACEITOS, QUANTOS, casar, por_regra
from ..models import Campo as CampoDb
from ..models import Indicador as IndicadorDb
from ..models import SegmentoKpi as KpiDb
from ..permissoes import exigir_dono, papel
from ..schemas import Indicador, IndicadorEdicao, IndicadorIn, Proposta
from .comum import PREFIXO, buscar, campos

router = APIRouter(prefix=PREFIXO, tags=["indicadores"])


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
    await buscar(sessao, organizacao_id, conexao_id)
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
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    colunas = await campos(sessao, conexao_id)
    if not colunas:
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

    tempos = [c for c in colunas if c.papel == "tempo"]
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
            resultado = casar(kpi, colunas)
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

    for bruto in por_regra(colunas, QUANTOS + len(descartados)):
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
    await buscar(sessao, organizacao_id, conexao_id)
    colunas = await campos(sessao, conexao_id)
    _conferir(body, colunas, body.agregacao)

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
    await buscar(sessao, organizacao_id, conexao_id)
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
    _conferir(indicador, await campos(sessao, conexao_id), indicador.agregacao)

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
