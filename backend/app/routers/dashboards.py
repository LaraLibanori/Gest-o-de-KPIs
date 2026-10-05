from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from ..auth import CurrentUser
from ..calculo import JANELA_PADRAO, calcular
from ..db import Sessao, entrar
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
    return (await _montar_todos(sessao, organizacao_id, [linha], janela))[0]


async def _montar_todos(
    sessao: Sessao, organizacao_id: UUID, linhas: list[DashboardDb], janela: str
) -> list[Dashboard]:
    vinculos: dict[UUID, list[UUID]] = {linha.id: [] for linha in linhas}
    for v in await sessao.scalars(
        select(VinculoDb)
        .where(VinculoDb.dashboard_id.in_(list(vinculos) or [None]))
        .order_by(VinculoDb.ordem)
    ):
        vinculos[v.dashboard_id].append(v.indicador_id)

    todos = {i for ids in vinculos.values() for i in ids}
    por_id = {
        i.id: i
        for i in await sessao.scalars(
            select(IndicadorDb).where(IndicadorDb.id.in_(list(todos) or [None]))
        )
    }

    por_conexao: dict[UUID, list[IndicadorDb]] = {}
    for indicador in por_id.values():
        por_conexao.setdefault(indicador.conexao_id, []).append(indicador)

    saida: dict[UUID, ItemDashboard] = {}
    nomes: dict[UUID, str] = {}

    # Cada conexao e aberta uma vez so, mesmo que varios dashboards a usem.
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
        nomes[conexao_id] = conexao.nome
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

    resposta = []
    for linha in linhas:
        ids = [i for i in vinculos[linha.id] if i in saida]
        usadas = dict.fromkeys(por_id[i].conexao_id for i in ids)
        resposta.append(
            Dashboard(
                id=linha.id,
                nome=linha.nome,
                descricao=linha.descricao,
                criado_em=linha.criado_em,
                indicadores=[saida[i] for i in ids],
                conexoes=[nomes[c] for c in usadas if c in nomes],
            )
        )
    return resposta


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
    return await _montar_todos(sessao, organizacao_id, linhas, janela)


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
    await entrar(sessao, user)
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
    await entrar(sessao, user)
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
    ids = list(dict.fromkeys(dados.indicadores))

    donos = set(
        await sessao.scalars(
            select(ConexaoDb.id).where(ConexaoDb.organizacao_id == organizacao_id)
        )
    )
    conexoes = dict(
        (
            await sessao.execute(
                select(IndicadorDb.id, IndicadorDb.conexao_id).where(
                    IndicadorDb.id.in_(ids)
                )
            )
        ).all()
    )
    if any(conexoes.get(i) not in donos for i in ids):
        raise HTTPException(422, "indicador não pertence à organização")

    await sessao.execute(
        delete(VinculoDb).where(VinculoDb.dashboard_id == dashboard_id)
    )
    sessao.add_all(
        VinculoDb(dashboard_id=dashboard_id, indicador_id=i, ordem=ordem)
        for ordem, i in enumerate(ids)
    )
    await sessao.commit()
    await entrar(sessao, user)
    return await _montar(sessao, organizacao_id, linha, JANELA_PADRAO)
