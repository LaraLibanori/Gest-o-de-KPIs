from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select, text

from ..auth import CurrentUser
from ..db import Sessao
from ..models import Convite as ConviteDb
from ..models import Membro as MembroDb
from ..models import Organizacao as OrganizacaoDb
from ..models import Perfil as PerfilDb
from ..permissoes import papel as _papel
from ..schemas import Convite, ConviteIn, Membro, Organizacao, OrganizacaoIn

router = APIRouter(prefix="/organizacoes", tags=["organizações"])


@router.get("", response_model=list[Organizacao])
async def listar(user: CurrentUser, sessao: Sessao):
    linhas = await sessao.execute(
        select(OrganizacaoDb, MembroDb.papel)
        .join(MembroDb, MembroDb.organizacao_id == OrganizacaoDb.id)
        .where(MembroDb.usuario_id == user.id)
        .order_by(OrganizacaoDb.criada_em.desc())
    )
    return [
        Organizacao(id=o.id, nome=o.nome, criada_em=o.criada_em, papel=papel)
        for o, papel in linhas
    ]


@router.post("", response_model=Organizacao, status_code=201)
async def criar(body: OrganizacaoIn, user: CurrentUser, sessao: Sessao):
    # A funcao cria a organizacao e o dono de uma vez: pela RLS, quem cria ainda
    # nao e membro e nao conseguiria inserir a si mesmo.
    linha = (
        await sessao.execute(
            text("select id, nome, criada_em from public.criar_organizacao(:nome)"),
            {"nome": body.nome},
        )
    ).one()
    await sessao.commit()
    return Organizacao(
        id=linha.id, nome=linha.nome, criada_em=linha.criada_em, papel="dono"
    )


@router.delete("/{organizacao_id}", status_code=204)
async def remover(organizacao_id: UUID, user: CurrentUser, sessao: Sessao):
    if await _papel(sessao, organizacao_id, user.id) != "dono":
        raise HTTPException(403, "só o dono pode apagar a organização")
    await sessao.execute(
        delete(OrganizacaoDb).where(OrganizacaoDb.id == organizacao_id)
    )
    await sessao.commit()


@router.get("/{organizacao_id}/membros", response_model=list[Membro])
async def listar_membros(organizacao_id: UUID, user: CurrentUser, sessao: Sessao):
    await _papel(sessao, organizacao_id, user.id)
    linhas = await sessao.execute(
        select(MembroDb, PerfilDb)
        .join(PerfilDb, PerfilDb.id == MembroDb.usuario_id)
        .where(MembroDb.organizacao_id == organizacao_id)
        .order_by(MembroDb.criado_em)
    )
    return [
        Membro(
            usuario_id=m.usuario_id,
            email=p.email,
            nome=p.nome,
            papel=m.papel,
            criado_em=m.criado_em,
        )
        for m, p in linhas
    ]


@router.get("/{organizacao_id}/convites", response_model=list[Convite])
async def listar_convites(organizacao_id: UUID, user: CurrentUser, sessao: Sessao):
    await _papel(sessao, organizacao_id, user.id)
    linhas = await sessao.scalars(
        select(ConviteDb)
        .where(ConviteDb.organizacao_id == organizacao_id)
        .order_by(ConviteDb.criado_em)
    )
    return [
        Convite(
            id=c.id,
            email=c.email,
            papel=c.papel,
            situacao="pendente",
            criado_em=c.criado_em,
        )
        for c in linhas
    ]


@router.post("/{organizacao_id}/convites", response_model=Convite, status_code=201)
async def convidar(
    organizacao_id: UUID, body: ConviteIn, user: CurrentUser, sessao: Sessao
):
    if await _papel(sessao, organizacao_id, user.id) != "dono":
        raise HTTPException(403, "só o dono pode convidar")

    email = body.email.lower()
    convidado = await sessao.scalar(
        text("select public.usuario_por_email(:email)"), {"email": email}
    )

    if convidado is not None:
        ja_esta = await sessao.scalar(
            select(MembroDb.usuario_id).where(
                MembroDb.organizacao_id == organizacao_id,
                MembroDb.usuario_id == convidado,
            )
        )
        if ja_esta:
            raise HTTPException(409, "essa pessoa já está na organização")

        novo = MembroDb(
            organizacao_id=organizacao_id, usuario_id=convidado, papel=body.papel
        )
        sessao.add(novo)
        await sessao.flush()
        resposta = Convite(
            id=None,
            email=email,
            papel=novo.papel,
            situacao="membro",
            criado_em=novo.criado_em,
        )
        await sessao.commit()
        return resposta

    # Sem conta ainda: fica pendente e o trigger converte quando ela se cadastrar.
    pendente = await sessao.scalar(
        select(ConviteDb).where(
            ConviteDb.organizacao_id == organizacao_id, ConviteDb.email == email
        )
    )
    if pendente:
        raise HTTPException(409, "essa pessoa já foi convidada")

    convite = ConviteDb(
        organizacao_id=organizacao_id,
        email=email,
        papel=body.papel,
        convidado_por=user.id,
    )
    sessao.add(convite)
    await sessao.flush()
    resposta = Convite(
        id=convite.id,
        email=email,
        papel=convite.papel,
        situacao="pendente",
        criado_em=convite.criado_em,
    )
    await sessao.commit()
    return resposta


@router.delete("/{organizacao_id}/convites/{convite_id}", status_code=204)
async def cancelar_convite(
    organizacao_id: UUID, convite_id: UUID, user: CurrentUser, sessao: Sessao
):
    if await _papel(sessao, organizacao_id, user.id) != "dono":
        raise HTTPException(403, "só o dono pode cancelar convite")
    resultado = await sessao.execute(
        delete(ConviteDb).where(
            ConviteDb.id == convite_id, ConviteDb.organizacao_id == organizacao_id
        )
    )
    if resultado.rowcount == 0:
        raise HTTPException(404, "convite não encontrado")
    await sessao.commit()


@router.delete("/{organizacao_id}/membros/{usuario_id}", status_code=204)
async def remover_membro(
    organizacao_id: UUID, usuario_id: UUID, user: CurrentUser, sessao: Sessao
):
    meu_papel = await _papel(sessao, organizacao_id, user.id)
    # Dono tira quem quiser; membro só sai por conta própria.
    if meu_papel != "dono" and usuario_id != user.id:
        raise HTTPException(403, "só o dono pode remover outra pessoa")

    # for_update trava as linhas: dois pedidos ao mesmo tempo nao zeram os donos.
    donos = (
        await sessao.scalars(
            select(MembroDb.usuario_id)
            .where(MembroDb.organizacao_id == organizacao_id, MembroDb.papel == "dono")
            .with_for_update()
        )
    ).all()
    alvo = await sessao.scalar(
        select(MembroDb.papel).where(
            MembroDb.organizacao_id == organizacao_id,
            MembroDb.usuario_id == usuario_id,
        )
    )
    if alvo is None:
        raise HTTPException(404, "essa pessoa não está na organização")
    if alvo == "dono" and len(donos) <= 1:
        raise HTTPException(409, "a organização ficaria sem dono")

    await sessao.execute(
        delete(MembroDb).where(
            MembroDb.organizacao_id == organizacao_id,
            MembroDb.usuario_id == usuario_id,
        )
    )
    await sessao.commit()
