from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select

from ..auth import CurrentUser
from ..calculo import JANELA_PADRAO, calcular, compor
from ..db import Sessao
from ..formula import FormulaInvalida, analisar, derivar
from ..indicadores import (
    PAPEIS_ACEITOS,
    QUANTOS,
    casar,
    formas_possiveis,
    por_regra,
    sugerir_grafico,
)
from ..introspeccao import TEMPO, identificador
from ..llm import sugerir_graficos
from ..models import Campo as CampoDb
from ..models import Dashboard as DashboardDb
from ..models import DashboardIndicador as VinculoDb
from ..models import Indicador as IndicadorDb
from ..models import SegmentoKpi as KpiDb
from ..permissoes import exigir_dono, papel
from ..schemas import (
    JANELA,
    Campo,
    CampoCalculadoIn,
    CampoCalculadoPatch,
    Composicao,
    Dimensao,
    Indicador,
    IndicadorCalculado,
    IndicadorEdicao,
    IndicadorIn,
    Painel,
    Proposta,
    Quebra,
    SugestaoGrafico,
)
from .comum import PREFIXO, buscar, campos, consultar

router = APIRouter(prefix=PREFIXO, tags=["indicadores"])


# Nem chave nem data: quebrar por id so rende top-10, e a data e o eixo.
def _dimensoes(catalogo: list[CampoDb], tempos: set) -> list[Dimensao]:
    return [
        Dimensao(coluna=c.coluna, rotulo=c.rotulo or c.coluna)
        for c in catalogo
        if c.papel == "dimensao"
        and c.coluna not in tempos
        and not identificador(c.coluna)
        and not c.tipo.startswith(TEMPO)
    ]


def _conferir(dados, campos: list[CampoDb], agregacao: str) -> None:
    forma = getattr(dados, "grafico", None)
    if forma and forma not in formas_possiveis(dados):
        raise HTTPException(422, f"{forma} precisa de mais um campo para funcionar")
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
    await sessao.flush()

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
                    "grafico": "numero",
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
    # So mexe na forma se a escolhida deixou de caber; nao apaga o que a pessoa pediu.
    if "grafico" not in mudancas and indicador.grafico not in formas_possiveis(
        indicador
    ):
        indicador.grafico = sugerir_grafico(indicador.dimensao)
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
    forcar: bool = False,
):
    await exigir_dono(sessao, organizacao_id, user.id, "apagar indicador")
    await buscar(sessao, organizacao_id, conexao_id)
    # Apagar o indicador leva junto o vinculo do dashboard: avisar antes.
    dashboards = list(
        await sessao.scalars(
            select(DashboardDb.nome)
            .join(VinculoDb, VinculoDb.dashboard_id == DashboardDb.id)
            .where(
                VinculoDb.indicador_id == indicador_id,
                DashboardDb.organizacao_id == organizacao_id,
            )
        )
    )
    if dashboards and not forcar:
        raise HTTPException(
            409,
            "este indicador está em " + ", ".join(dashboards) + " e vai sumir de lá",
        )

    resultado = await sessao.execute(
        delete(IndicadorDb).where(
            IndicadorDb.id == indicador_id, IndicadorDb.conexao_id == conexao_id
        )
    )
    if resultado.rowcount == 0:
        raise HTTPException(404, "indicador não encontrado")
    await sessao.commit()


async def _em_uso(sessao, conexao_id: UUID, coluna: str) -> int:
    return int(
        await sessao.scalar(
            select(func.count())
            .select_from(IndicadorDb)
            .where(IndicadorDb.conexao_id == conexao_id, IndicadorDb.coluna == coluna)
        )
        or 0
    )


async def _conferir_formula(
    sessao: Sessao, conexao_id: UUID, nome: str, formula: str
) -> None:
    """Rejeita antes de gravar: formula que aponta para campo posterior é ciclo."""
    catalogo = await campos(sessao, conexao_id)
    base = {c.coluna for c in catalogo if not c.formula and c.coluna != nome}
    try:
        analisar(formula, base, base)
    except FormulaInvalida as e:
        raise HTTPException(422, str(e)) from e


@router.get("/{conexao_id}/campos", response_model=list[Campo])
async def listar_campos(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await papel(sessao, organizacao_id, user.id)
    await buscar(sessao, organizacao_id, conexao_id)
    saida = []
    for campo in await campos(sessao, conexao_id):
        if not campo.formula:
            continue
        campo.em_uso = await _em_uso(sessao, conexao_id, campo.coluna)
        saida.append(campo)
    return saida


@router.post("/{conexao_id}/campos", response_model=Campo, status_code=201)
async def criar_campo(
    organizacao_id: UUID,
    conexao_id: UUID,
    dados: CampoCalculadoIn,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "criar campo calculado")
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    if not conexao.tabela_fato:
        raise HTTPException(422, "escolha a tabela fato antes de criar campo")
    if any(c.coluna == dados.nome for c in await campos(sessao, conexao_id)):
        raise HTTPException(409, "esse nome já existe no catálogo")
    await _conferir_formula(sessao, conexao_id, dados.nome, dados.formula)

    ultimo = await sessao.scalar(
        select(func.coalesce(func.max(CampoDb.ordem), 0)).where(
            CampoDb.conexao_id == conexao_id
        )
    )
    campo = CampoDb(
        conexao_id=conexao_id,
        coluna=dados.nome,
        tipo="numeric",
        cardinalidade=None,
        papel=dados.papel,
        rotulo=dados.rotulo,
        formula=dados.formula,
        confirmado=True,
        ordem=ultimo + 1,
    )
    sessao.add(campo)
    await sessao.commit()
    campo.em_uso = 0
    return campo


@router.patch("/{conexao_id}/campos/{campo_id}", response_model=Campo)
async def ajustar_campo(
    organizacao_id: UUID,
    conexao_id: UUID,
    campo_id: UUID,
    dados: CampoCalculadoPatch,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "editar campo calculado")
    await buscar(sessao, organizacao_id, conexao_id)
    campo = await sessao.scalar(
        select(CampoDb).where(CampoDb.id == campo_id, CampoDb.conexao_id == conexao_id)
    )
    if campo is None or not campo.formula:
        raise HTTPException(404, "campo calculado não encontrado")
    if dados.formula is not None:
        await _conferir_formula(sessao, conexao_id, campo.coluna, dados.formula)
        campo.formula = dados.formula
    if dados.rotulo is not None:
        campo.rotulo = dados.rotulo
    if dados.papel is not None:
        campo.papel = dados.papel
    campo.em_uso = await _em_uso(sessao, conexao_id, campo.coluna)
    await sessao.commit()
    return campo


@router.delete("/{conexao_id}/campos/{campo_id}", status_code=204)
async def remover_campo(
    organizacao_id: UUID,
    conexao_id: UUID,
    campo_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    forcar: bool = False,
):
    await exigir_dono(sessao, organizacao_id, user.id, "apagar campo calculado")
    await buscar(sessao, organizacao_id, conexao_id)
    campo = await sessao.scalar(
        select(CampoDb).where(CampoDb.id == campo_id, CampoDb.conexao_id == conexao_id)
    )
    if campo is None or not campo.formula:
        raise HTTPException(404, "campo calculado não encontrado")

    em_uso = await _em_uso(sessao, conexao_id, campo.coluna)
    if em_uso and not forcar:
        raise HTTPException(
            409,
            f"{em_uso} indicador{'es' if em_uso > 1 else ''} usa"
            f"{'m' if em_uso > 1 else ''} este campo e vai parar de funcionar",
        )

    resultado = await sessao.execute(
        delete(CampoDb).where(
            CampoDb.id == campo_id,
            CampoDb.conexao_id == conexao_id,
            CampoDb.formula.is_not(None),
        )
    )
    if resultado.rowcount == 0:
        raise HTTPException(404, "campo calculado não encontrado")
    await sessao.commit()


# So troca a forma de quem a llm acertou: o que ela sugerir fora do possivel cai.
@router.post("/{conexao_id}/indicadores/graficos", response_model=SugestaoGrafico)
async def sugerir_formas(
    organizacao_id: UUID, conexao_id: UUID, user: CurrentUser, sessao: Sessao
):
    await exigir_dono(sessao, organizacao_id, user.id, "sugerir gráficos")
    await buscar(sessao, organizacao_id, conexao_id)
    linhas = list(
        await sessao.scalars(
            select(IndicadorDb)
            .where(IndicadorDb.conexao_id == conexao_id)
            .order_by(IndicadorDb.ordem)
        )
    )
    escolhas = await sugerir_graficos(
        [
            {
                "nome": i.nome,
                "agregacao": i.agregacao,
                "campo": i.coluna,
                "quebra": i.dimensao,
                "tempo": i.tempo,
                "periodo": i.periodo,
                "formas": formas_possiveis(i),
            }
            for i in linhas
        ]
    )

    # A llm demora; relê para não escrever por cima de quem editou nesse meio tempo.
    linhas = list(
        await sessao.scalars(
            select(IndicadorDb)
            .where(IndicadorDb.conexao_id == conexao_id)
            .order_by(IndicadorDb.ordem)
            .execution_options(populate_existing=True)
        )
    )
    aplicadas = 0
    for indicador in linhas:
        forma = escolhas.get(indicador.nome)
        if (
            forma
            and forma != indicador.grafico
            and forma in formas_possiveis(indicador)
        ):
            indicador.grafico = forma
            aplicadas += 1

    await sessao.flush()
    resposta = SugestaoGrafico(
        aplicadas=aplicadas,
        indicadores=[Indicador.model_validate(i) for i in linhas],
    )
    await sessao.commit()
    return resposta


# Abre o banco do cliente uma vez e calcula todos os indicadores nele.
@router.get("/{conexao_id}/painel", response_model=Painel)
async def painel(
    organizacao_id: UUID,
    conexao_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    janela: JANELA = JANELA_PADRAO,
    serie: bool = True,
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    linhas = list(
        await sessao.scalars(
            select(IndicadorDb)
            .where(IndicadorDb.conexao_id == conexao_id)
            .order_by(IndicadorDb.ordem)
        )
    )
    saida = [IndicadorCalculado.model_validate(i) for i in linhas]
    catalogo = await campos(sessao, conexao_id)
    dimensoes = _dimensoes(catalogo, {i.tempo for i in linhas})
    tempo = next((i.tempo for i in linhas if i.tempo), None)

    # Campo calculado que nao fecha aponta para coluna que foi embora na tabela.
    _, quebrados = derivar(catalogo)
    avisos = [
        f"o campo calculado {nome} ficou de fora: a fórmula aponta para uma "
        "coluna que não existe mais na tabela"
        for nome in quebrados
    ]

    if not linhas or not conexao.tabela_fato:
        return Painel(
            tabela=conexao.tabela_fato,
            janela=janela,
            indicadores=saida,
            dimensoes=dimensoes,
            janelavel=tempo is not None,
            avisos=avisos,
        )

    tabela = conexao.tabela_fato
    calculados, _ = derivar(catalogo)
    try:
        valores = await consultar(
            conexao,
            lambda externa: calcular(
                externa, tabela, linhas, janela, com_serie=serie, calculados=calculados
            ),
        )
    except HTTPException as e:
        return Painel(
            tabela=tabela,
            janela=janela,
            indicadores=saida,
            dimensoes=dimensoes,
            janelavel=tempo is not None,
            avisos=avisos,
            erro=e.detail,
        )

    for calculado in saida:
        dados = valores.get(str(calculado.id), {})
        calculado.valor = dados.get("valor")
        calculado.anterior = dados.get("anterior")
        calculado.variacao = dados.get("variacao")
        calculado.serie = [Quebra(**q) for q in dados.get("serie", [])]
        calculado.erro = dados.get("erro")
    return Painel(
        tabela=tabela,
        janela=janela,
        indicadores=saida,
        dimensoes=dimensoes,
        janelavel=tempo is not None,
        avisos=avisos,
    )


# A composicao e a pergunta "onde isso esta indo": um indicador, uma dimensao.
@router.get("/{conexao_id}/composicao", response_model=Composicao)
async def composicao(
    organizacao_id: UUID,
    conexao_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    indicador: UUID,
    dimensao: str = Query(min_length=1, max_length=200),
    janela: JANELA = JANELA_PADRAO,
    limite: int = Query(10, ge=1, le=30),
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    if not conexao.tabela_fato:
        raise HTTPException(409, "escolha a tabela fato antes")

    alvo = await sessao.scalar(
        select(IndicadorDb).where(
            IndicadorDb.id == indicador, IndicadorDb.conexao_id == conexao_id
        )
    )
    if alvo is None:
        raise HTTPException(404, "indicador não encontrado")
    catalogo = await campos(sessao, conexao_id)
    tempos = set(
        await sessao.scalars(
            select(IndicadorDb.tempo).where(IndicadorDb.conexao_id == conexao_id)
        )
    )
    if dimensao not in {d.coluna for d in _dimensoes(catalogo, tempos)}:
        raise HTTPException(422, "essa coluna não serve para quebrar o indicador")

    calculados, _ = derivar(catalogo)
    pontos, total = await consultar(
        conexao,
        lambda externa: compor(
            externa,
            conexao.tabela_fato,
            alvo,
            dimensao,
            janela,
            limite,
            calculados,
        ),
    )
    rotulo = next(
        (c.rotulo or c.coluna for c in catalogo if c.coluna == dimensao),
        dimensao,
    )
    return Composicao(
        coluna=dimensao,
        rotulo=rotulo,
        total=total,
        pontos=[Quebra(**p) for p in pontos],
    )
