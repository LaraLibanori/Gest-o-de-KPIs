"""convites"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

ROLE = "kpi_api"


def upgrade() -> None:
    op.create_table(
        "convites",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organizacao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column("convidado_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("papel in ('dono', 'membro')", name="convites_papel_check"),
        sa.ForeignKeyConstraint(
            ["organizacao_id"], ["organizacoes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["convidado_por"], ["auth.users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("create unique index convites_unico on convites (organizacao_id, email)")
    op.execute("create index ix_convites_email on convites (email)")

    op.execute(f"grant select, insert, delete on convites to {ROLE}")
    op.execute("alter table convites enable row level security")
    op.execute(
        """
        create policy "convites da minha organizacao" on convites
          for all using (organizacao_id in (select public.organizacoes_do_usuario()))
          with check (organizacao_id in (select public.organizacoes_do_usuario()))
        """
    )

    # Quem se cadastra depois do convite ja entra na organizacao.
    op.execute(
        """
        create function public.aceitar_convites() returns trigger
        language plpgsql security definer set search_path = public as $$
        begin
          insert into organizacao_membros (organizacao_id, usuario_id, papel)
          select c.organizacao_id, new.id, c.papel
          from convites c where c.email = new.email
          on conflict do nothing;
          delete from convites where email = new.email;
          return new;
        end;
        $$
        """
    )
    op.execute(
        """
        create trigger ao_criar_perfil after insert on perfis
        for each row execute function public.aceitar_convites()
        """
    )


def downgrade() -> None:
    op.execute("drop trigger if exists ao_criar_perfil on perfis")
    op.execute("drop function if exists public.aceitar_convites()")
    op.drop_table("convites")
