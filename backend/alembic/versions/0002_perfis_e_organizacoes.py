"""perfis e organizacoes"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

USUARIO = "auth.users.id"


def upgrade() -> None:
    op.drop_table("indicadores")
    op.drop_table("dashboards")
    op.drop_table("vendas")

    op.create_table(
        "perfis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["id"], [USUARIO], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "organizacoes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("criada_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["criada_por"], [USUARIO], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "organizacao_membros",
        sa.Column("organizacao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "papel in ('dono', 'membro')", name="organizacao_membros_papel_check"
        ),
        sa.ForeignKeyConstraint(
            ["organizacao_id"], ["organizacoes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], [USUARIO], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organizacao_id", "usuario_id"),
    )
    op.create_index(
        "ix_organizacao_membros_usuario_id", "organizacao_membros", ["usuario_id"]
    )

    # Quem se cadastra ganha o perfil na hora, sem depender da aplicação.
    op.execute(
        """
        create function public.criar_perfil() returns trigger
        language plpgsql security definer set search_path = public as $$
        begin
          insert into perfis (id, email) values (new.id, new.email)
          on conflict (id) do nothing;
          return new;
        end;
        $$
        """
    )
    op.execute(
        """
        create trigger ao_criar_usuario after insert on auth.users
        for each row execute function public.criar_perfil()
        """
    )
    op.execute(
        """
        insert into perfis (id, email)
        select id, email from auth.users where email is not null
        on conflict (id) do nothing
        """
    )

    # security definer evita a policy consultar a propria tabela e recursar.
    op.execute(
        """
        create function public.organizacoes_do_usuario() returns setof uuid
        language sql security definer stable set search_path = public as $$
          select organizacao_id from organizacao_membros where usuario_id = auth.uid()
        $$
        """
    )

    for tabela in ("perfis", "organizacoes", "organizacao_membros"):
        op.execute(f"alter table {tabela} enable row level security")

    op.execute(
        """
        create policy "perfil proprio ou de quem divide organizacao" on perfis
          for select using (
            id = auth.uid()
            or exists (
              select 1 from organizacao_membros m
              where m.usuario_id = perfis.id
                and m.organizacao_id in (select public.organizacoes_do_usuario())
            )
          )
        """
    )
    op.execute(
        """
        create policy "organizacao de que participo" on organizacoes
          for all using (id in (select public.organizacoes_do_usuario()))
          with check (criada_por = auth.uid())
        """
    )
    op.execute(
        """
        create policy "membros da minha organizacao" on organizacao_membros
          for all using (organizacao_id in (select public.organizacoes_do_usuario()))
          with check (organizacao_id in (select public.organizacoes_do_usuario()))
        """
    )


def downgrade() -> None:
    # Voltar para a 0001 recriaria as tabelas de KPI. Melhor recusar.
    raise NotImplementedError("sem downgrade: recrie o banco a partir da 0001")
