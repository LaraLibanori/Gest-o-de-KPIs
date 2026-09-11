from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# So para as chaves estrangeiras resolverem: o schema auth e do Supabase.
sa.Table(
    "users",
    Base.metadata,
    sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
    schema="auth",
)

USUARIO = "auth.users.id"


# Login e senha ficam no auth do Supabase; aqui so o que e da aplicacao.
class Perfil(Base):
    __tablename__ = "perfis"
    __table_args__ = (
        sa.Index("perfis_email_unico", sa.text("lower(email)"), unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(USUARIO, ondelete="CASCADE"), primary_key=True
    )
    email: Mapped[str] = mapped_column(Text)
    nome: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Organizacao(Base):
    __tablename__ = "organizacoes"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nome: Mapped[str] = mapped_column(Text)
    criada_por: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(USUARIO, ondelete="CASCADE")
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# E esta tabela que faz o compartilhamento: quem esta aqui ve a organizacao.
class Membro(Base):
    __tablename__ = "organizacao_membros"
    __table_args__ = (
        sa.CheckConstraint(
            "papel in ('dono', 'membro')", name="organizacao_membros_papel_check"
        ),
    )

    organizacao_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("organizacoes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(USUARIO, ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    papel: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Convite de quem ainda nao tem conta. Ao se cadastrar, um trigger converte
# o convite em membro e apaga a linha.
class Convite(Base):
    __tablename__ = "convites"
    __table_args__ = (
        sa.CheckConstraint("papel in ('dono', 'membro')", name="convites_papel_check"),
        sa.Index("convites_unico", "organizacao_id", "email", unique=True),
        sa.Index("ix_convites_email", "email"),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organizacao_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizacoes.id", ondelete="CASCADE")
    )
    email: Mapped[str] = mapped_column(Text)
    papel: Mapped[str] = mapped_column(Text)
    convidado_por: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(USUARIO, ondelete="CASCADE")
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Banco PostgreSQL da empresa. A senha fica cifrada, nunca em texto puro.
class Conexao(Base):
    __tablename__ = "conexoes"
    __table_args__ = (
        sa.CheckConstraint(
            "etapa in ('tabela', 'negocio', 'catalogo', 'indicadores', 'pronta')",
            name="conexoes_etapa_check",
        ),
        sa.Index("conexoes_nome_unico", "organizacao_id", "nome", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    organizacao_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizacoes.id", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(Text)
    host: Mapped[str] = mapped_column(Text)
    porta: Mapped[int] = mapped_column(Integer)
    banco: Mapped[str] = mapped_column(Text)
    usuario: Mapped[str] = mapped_column(Text)
    senha_cifrada: Mapped[str] = mapped_column(Text)
    tabela_fato: Mapped[str | None] = mapped_column(Text, nullable=True)
    segmento: Mapped[str | None] = mapped_column(
        Text, ForeignKey("segmentos.chave", ondelete="SET NULL"), nullable=True
    )
    tabela_tipo: Mapped[str | None] = mapped_column(Text, nullable=True)
    descricao_negocio: Mapped[str | None] = mapped_column(Text, nullable=True)
    etapa: Mapped[str] = mapped_column(Text, server_default="pronta")
    verificada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verificacao_erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    criada_por: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey(USUARIO, ondelete="CASCADE")
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Uma coluna da tabela fato, com o papel que ela cumpre no indicador.
class Campo(Base):
    __tablename__ = "catalogo_campos"
    __table_args__ = (
        sa.CheckConstraint(
            "papel in ('metrica', 'dimensao', 'tempo', 'ignorar')",
            name="catalogo_campos_papel_check",
        ),
        sa.Index("catalogo_campos_unico", "conexao_id", "coluna", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    conexao_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conexoes.id", ondelete="CASCADE")
    )
    coluna: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text)
    cardinalidade: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    papel: Mapped[str] = mapped_column(Text)
    rotulo: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmado: Mapped[bool] = mapped_column(Boolean, server_default=sa.false())
    ordem: Mapped[int] = mapped_column(Integer)


# Ramo de negocio. Lista fechada, semeada na migration: e ela que faz o cache
# de indicadores acertar, porque texto livre nunca repete.
class Segmento(Base):
    __tablename__ = "segmentos"

    chave: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text)
    ordem: Mapped[int] = mapped_column(Integer)


# Indicador que costuma valer para o segmento, sem saber nada da tabela de
# ninguem. So vira indicador de verdade depois de casar com o catalogo.
class SegmentoKpi(Base):
    __tablename__ = "segmento_kpis"
    __table_args__ = (
        sa.CheckConstraint(
            "agregacao in ('soma', 'media', 'contagem', 'distintos', 'minimo', 'maximo')",
            name="segmento_kpis_agregacao_check",
        ),
        sa.Index("segmento_kpis_unico", "segmento", "nome", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    segmento: Mapped[str] = mapped_column(
        Text, ForeignKey("segmentos.chave", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(Text)
    pista: Mapped[str | None] = mapped_column(Text, nullable=True)
    agregacao: Mapped[str] = mapped_column(Text)
    papel: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer)


# Cache da classificacao: md5 do texto normalizado aponta para o segmento.
class Classificacao(Base):
    __tablename__ = "classificacoes"

    chave: Mapped[str] = mapped_column(Text, primary_key=True)
    texto: Mapped[str] = mapped_column(Text)
    segmento: Mapped[str] = mapped_column(
        Text, ForeignKey("segmentos.chave", ondelete="CASCADE")
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# Indicador ja casado com as colunas da conexao. Guarda o nome da coluna e nao
# o id do campo: o catalogo e refeito do zero a cada leitura da tabela.
class Indicador(Base):
    __tablename__ = "indicadores"
    __table_args__ = (
        sa.CheckConstraint(
            "agregacao in ('soma', 'media', 'contagem', 'distintos', 'minimo', 'maximo')",
            name="indicadores_agregacao_check",
        ),
        sa.CheckConstraint(
            "origem in ('regra', 'segmento', 'manual')",
            name="indicadores_origem_check",
        ),
        sa.CheckConstraint(
            "periodo is null or periodo in"
            " ('sempre', 'ultimos_7_dias', 'ultimos_30_dias', 'ultimos_90_dias', 'ano_atual')",
            name="indicadores_periodo_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    conexao_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conexoes.id", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(Text)
    agregacao: Mapped[str] = mapped_column(Text)
    coluna: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tempo: Mapped[str | None] = mapped_column(Text, nullable=True)
    periodo: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(Text)
    confirmado: Mapped[bool] = mapped_column(Boolean, server_default=sa.false())
    ordem: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
