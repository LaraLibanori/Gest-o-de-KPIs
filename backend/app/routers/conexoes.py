from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from ..auth import CurrentUser
from ..cripto import cifrar
from ..db import Sessao
from ..introspeccao import listar_esquemas, listar_relacoes
from ..models import Conexao as ConexaoDb
from ..models import Indicador as IndicadorDb
from ..permissoes import exigir_dono, papel
from ..schemas import Conexao, ConexaoIn, ConexaoPatch, ConexaoProva, Verificacao
from .comum import PREFIXO, buscar, consultar

router = APIRouter(prefix=PREFIXO, tags=["conexões"])

DUPLICADO = "esta organização já tem uma conexão chamada {nome}"

# Colunas que aceitam ficar sem valor: nas outras, None daria 500 em coluna NOT NULL.
LIMPAVEIS = {
    "esquema",
    "tabela_fato",
    "tabela_tipo",
    "descricao_negocio",
    "segmento",
}


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
    await _garantir_nome_livre(sessao, organizacao_id, body.nome)

    nova = ConexaoDb(
        organizacao_id=organizacao_id,
        nome=body.nome,
        host=body.host,
        porta=body.porta,
        banco=body.banco,
        esquema=body.esquema,
        usuario=body.usuario,
        senha_cifrada=cifrar(body.senha),
        tabela_fato=body.tabela_fato,
        etapa="tabela",
        criada_por=user.id,
    )
    sessao.add(nova)
    try:
        await sessao.flush()
    except IntegrityError:
        await sessao.rollback()
        raise HTTPException(409, DUPLICADO.format(nome=body.nome)) from None
    await sessao.refresh(nova)
    resposta = Conexao.model_validate(nova)
    await sessao.commit()
    return resposta


async def _garantir_nome_livre(
    sessao: Sessao, organizacao_id: UUID, nome: str, ignorar: UUID | None = None
) -> None:
    filtros = [
        ConexaoDb.organizacao_id == organizacao_id,
        func.lower(ConexaoDb.nome) == nome.lower(),
    ]
    if ignorar is not None:
        filtros.append(ConexaoDb.id != ignorar)
    if await sessao.scalar(select(ConexaoDb.id).where(*filtros)):
        raise HTTPException(409, DUPLICADO.format(nome=nome))


async def _inspecionar(conexao: ConexaoDb, esquema: str | None) -> Verificacao:
    relacoes: list[dict] = []
    esquemas: list[str] = []
    erro: str | None = None

    async def _ler(externa):
        relacoes.extend(await listar_relacoes(externa, esquema))
        esquemas.extend(await listar_esquemas(externa))

    try:
        await consultar(conexao, _ler)
    except HTTPException as e:
        erro = e.detail

    return Verificacao(ok=erro is None, erro=erro, relacoes=relacoes, esquemas=esquemas)


@router.post("/provar", response_model=Verificacao)
async def provar(
    organizacao_id: UUID, body: ConexaoProva, user: CurrentUser, sessao: Sessao
):
    """Testa a credencial digitada sem criar nada."""
    await exigir_dono(sessao, organizacao_id, user.id, "testar conexão")
    provisoria = ConexaoDb(
        organizacao_id=organizacao_id,
        nome="prova",
        host=body.host,
        porta=body.porta,
        banco=body.banco,
        esquema=body.esquema,
        usuario=body.usuario,
        senha_cifrada=cifrar(body.senha),
        etapa="tabela",
        criada_por=user.id,
    )
    return await _inspecionar(provisoria, body.esquema)


@router.post("/{conexao_id}/verificar", response_model=Verificacao)
async def verificar(
    organizacao_id: UUID,
    conexao_id: UUID,
    user: CurrentUser,
    sessao: Sessao,
    esquema: str | None = None,
):
    await papel(sessao, organizacao_id, user.id)
    conexao = await buscar(sessao, organizacao_id, conexao_id)
    alvo = (esquema or "").strip() or conexao.esquema

    resultado = await _inspecionar(conexao, alvo)
    conexao.verificada_em = datetime.now(timezone.utc)
    conexao.verificacao_erro = resultado.erro
    await sessao.commit()
    return resultado


@router.patch("/{conexao_id}", response_model=Conexao)
async def avancar(
    organizacao_id: UUID,
    conexao_id: UUID,
    body: ConexaoPatch,
    user: CurrentUser,
    sessao: Sessao,
):
    await exigir_dono(sessao, organizacao_id, user.id, "editar conexão")
    conexao = await buscar(sessao, organizacao_id, conexao_id)

    mudancas: dict[str, object] = {}
    for campo in body.model_fields_set:
        if campo == "senha":
            if body.senha:
                mudancas["senha_cifrada"] = cifrar(body.senha)
            continue
        valor = getattr(body, campo)
        if valor is None and campo not in LIMPAVEIS:
            raise HTTPException(422, f"{campo} não pode ficar vazio")
        mudancas[campo] = valor

    if "nome" in mudancas and mudancas["nome"] != conexao.nome:
        await _garantir_nome_livre(
            sessao, organizacao_id, str(mudancas["nome"]), ignorar=conexao_id
        )

    if body.etapa == "pronta":
        tem = await sessao.scalar(
            select(IndicadorDb.id).where(IndicadorDb.conexao_id == conexao_id).limit(1)
        )
        if not tem:
            raise HTTPException(409, "defina ao menos um indicador antes de concluir")

    for campo, valor in mudancas.items():
        setattr(conexao, campo, valor)

    if body.credenciais or body.senha:
        conexao.verificada_em = None
        conexao.verificacao_erro = None

    try:
        await sessao.flush()
    except IntegrityError:
        await sessao.rollback()
        raise HTTPException(
            409, DUPLICADO.format(nome=mudancas.get("nome") or conexao.nome)
        ) from None
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
