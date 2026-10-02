from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from ..auth import CurrentUser
from ..calculo import JANELA_PADRAO, calcular
from ..db import Sessao
from ..formula import derivar
from ..models import Conexao as ConexaoDb
from ..models import Dashboard as DashboardDb
from ..models import DashboardIndicador as VinculoDb
from ..models import Indicador as IndicadorDb
from ..permissoes import exigir_dono, papel
from ..schemas import (
    JANELA,
    Dashboard,
    DashboardIn,
    DashboardIndicadoresIn,
    DashboardPatch,
    IndicadorCalculado,
    ItemDashboard,
    Quebra,
)
from .comum import campos, consultar

router = APIRouter(
    prefix="/organizacoes/{organizacao_id}/dashboards", tags=["dashboards"]
)


async def _montar(
    sessao: Sessao, organizacao_id: UUID, linha: DashboardDb, janela: str
) -> Dashboard:
    vinculos = list(
        await sessao.scalars(
            select(VinculoDb)
            .where(VinculoDb.dashboard_id == linha.id)
            .order_by(VinculoDb.ordem)
        )
    )
    indicadores = [
        i
        for i in await sessao.scalars(
            select(IndicadorDb).where(
                IndicadorDb.id.in_([v.indicador_id for v in vinculos] or [None])
            )
        )
    ]
    if not indicadores:
        return Dashboard(
            id=linha.id,
            nome=linha.nome,
            descricao=linha.descricao,
            criado_em=linha.criado_em,
        )

    por_conexao: dict[UUID, list] = {}
    for indicador in indicadores:
        por_conexao.setdefault(indicador.conexao_id, []).append(indicador)

    saida: dict[UUID, ItemDashboard] = {}
    nomes: list[str] = []

    # Cada conexao e aberta e fechada por conta propria: sao bancos diferentes.
    for conexao_id, grupo in por_conexao.items():
        conexao = await sessao.scalar(
            select(ConexaoDb).where(
                ConexaoDb.id == conexao_id, ConexaoDb.organizacao_id == organizacao_id
            )
        )
        if conexao is None or not conexao.tabela_fato:
            for indicador in grupo:
                saida[indicador.id] = _vazio(indicador, "conexão sem tabela fato", None)
            continue
        nomes.append(conexao.nome)
        calculados, _ = derivar(await campos(sessao, conexao_id))
        try:
            valores = await consultar(
                conexao,
                lambda externa, g=grupo, c=calculados, t=conexao.tabela_fato: calcular(
                    externa, t, g, janela, com_serie=True, calculados=c
                ),
            )
        except HTTPException as e:
            for indicador in grupo:
                saida[indicador.id] = _vazio(indicador, str(e.detail), conexao.nome)
            continue
        for indicador in grupo:
            calculado = IndicadorCalculado.model_validate(indicador)
            dados = valores.get(str(indicador.id), {})
            calculado.valor = dados.get("valor")
            calculado.anterior = dados.get("anterior")
            calculado.variacao = dados.get("variacao")
            calculado.serie = [Quebra(**q) for q in dados.get("serie", [])]
            calculado.erro = dados.get("erro")
            saida[indicador.id] = ItemDashboard(
                **calculado.model_dump(),
                conexao_id=conexao.id,
                conexao=conexao.nome,
            )

    return Dashboard(
        id=linha.id,
        nome=linha.nome,
        descricao=linha.descricao,
        criado_em=linha.criado_em,
        indicadores=[saida[i.id] for i in indicadores if i.id in saida],
        conexoes=nomes,
    )


def _vazio(indicador: IndicadorDb, erro: str, nome: str | None) -> ItemDashboard:
    base = IndicadorCalculado.model_validate(indicador)
    base.erro = erro
    return ItemDashboard(
        **base.model_dump(), conexao_id=indicador.conexao_id, conexao=nome or ""
    )


@router.get("", response_model=list[Dashboard])
async def listar(
    organizacao_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    janela: JANELA = JANELA_PADRAO,
):
    await papel(sessao, organizacao_id, user.id)
    linhas = list(
        await sessao.scalars(
            select(DashboardDb)
            .where(DashboardDb.organizacao_id == organizacao_id)
            .order_by(DashboardDb.criado_em.desc())
        )
    )
    return [await _montar(sessao, organizacao_id, linha, janela) for linha in linhas]


@router.post("", response_model=Dashboard, status_code=201)
async def criar(
    organizacao_id: UUID, dados: DashboardIn, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    if await sessao.scalar(
        select(DashboardDb).where(
            DashboardDb.organizacao_id == organizacao_id,
            func.lower(DashboardDb.nome) == dados.nome.strip().lower(),
        )
    ):
        raise HTTPException(409, "já existe um dashboard com esse nome")
    linha = DashboardDb(
        organizacao_id=organizacao_id,
        nome=dados.nome.strip(),
        descricao=dados.descricao,
        criado_por=user.id,
    )
    sessao.add(linha)
    await sessao.commit()
    return await _montar(sessao, organizacao_id, linha, JANELA_PADRAO)


async def _linha(sessao: Sessao, organizacao_id: UUID, dashboard_id: UUID):
    linha = await sessao.scalar(
        select(DashboardDb).where(
            DashboardDb.id == dashboard_id,
            DashboardDb.organizacao_id == organizacao_id,
        )
    )
    if linha is None:
        raise HTTPException(404, "dashboard não encontrado")
    return linha


@router.get("/{dashboard_id}", response_model=Dashboard)
async def ver(
    organizacao_id: UUID,
    dashboard_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    janela: JANELA = JANELA_PADRAO,
):
    await papel(sessao, organizacao_id, user.id)
    return await _montar(
        sessao,
        organizacao_id,
        await _linha(sessao, organizacao_id, dashboard_id),
        janela,
    )


@router.patch("/{dashboard_id}", response_model=Dashboard)
async def ajustar(
    organizacao_id: UUID,
    dashboard_id: UUID,
    dados: DashboardPatch,
    user: CurrentUser,
    sessao: Sessao,
):
    await papel(sessao, organizacao_id, user.id)
    linha = await _linha(sessao, organizacao_id, dashboard_id)
    if dados.nome is not None:
        if await sessao.scalar(
            select(DashboardDb).where(
                DashboardDb.organizacao_id == organizacao_id,
                DashboardDb.id != dashboard_id,
                func.lower(DashboardDb.nome) == dados.nome.strip().lower(),
            )
        ):
            raise HTTPException(409, "já existe um dashboard com esse nome")
        linha.nome = dados.nome.strip()
    if dados.descricao is not None:
        linha.descricao = dados.descricao
    await sessao.commit()
    return await _montar(sessao, organizacao_id, linha, JANELA_PADRAO)


@router.delete("/{dashboard_id}", status_code=204)
async def remover(
    organizacao_id: UUID, dashboard_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "apagar dashboard")
    await sessao.execute(
        delete(DashboardDb).where(
            DashboardDb.id == dashboard_id,
            DashboardDb.organizacao_id == organizacao_id,
        )
    )
    await sessao.commit()


@router.put("/{dashboard_id}/indicadores", response_model=Dashboard)
async def trocar_indicadores(
    organizacao_id: UUID,
    dashboard_id: UUID,
    dados: DashboardIndicadoresIn,
    user: CurrentUser,
    sessao: Sessao,
):
    await papel(sessao, organizacao_id, user.id)
    linha = await _linha(sessao, organizacao_id, dashboard_id)
    ids = dados.indicadores[:40]

    existentes = set(
        await sessao.scalars(
            select(IndicadorDb.conexao_id)
            .join(VinculoDb, VinculoDb.indicador_id == IndicadorDb.id)
            .where(VinculoDb.dashboard_id == dashboard_id)
        )
    )
    donos = {
        c
        for c in await sessao.scalars(
            select(ConexaoDb.id).where(ConexaoDb.organizacao_id == organizacao_id)
        )
    }
    if any(c not in donos for c in existentes):
        raise HTTPException(403, "esse dashboard tem indicador de outra organização")

    await sessao.execute(
        delete(VinculoDb).where(VinculoDb.dashboard_id == dashboard_id)
    )
    for ordem, indicador_id in enumerate(ids):
        pertence = await sessao.scalar(
            select(IndicadorDb.conexao_id).where(IndicadorDb.id == indicador_id)
        )
        if pertence is None or pertence not in donos:
            raise HTTPException(422, "indicador não pertence à organização")
        sessao.add(
            VinculoDb(dashboard_id=dashboard_id, indicador_id=indicador_id, ordem=ordem)
        )
    await sessao.commit()
    return await _montar(sessao, organizacao_id, linha, JANELA_PADRAO)
