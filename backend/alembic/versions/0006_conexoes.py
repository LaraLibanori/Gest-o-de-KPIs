"""conexoes"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

ROLE = "kpi_api"


def upgrade() -> None:
    op.create_table(
        "conexoes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("organizacao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("porta", sa.Integer(), nullable=False),
        sa.Column("banco", sa.Text(), nullable=False),
        sa.Column("usuario", sa.Text(), nullable=False),
        sa.Column("senha_cifrada", sa.Text(), nullable=False),
        sa.Column("tabela_fato", sa.Text(), nullable=True),
        sa.Column("verificada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verificacao_erro", sa.Text(), nullable=True),
        sa.Column("criada_por", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organizacao_id"], ["organizacoes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["criada_por"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "create unique index conexoes_nome_unico on conexoes (organizacao_id, nome)"
    )

    op.execute(f"grant select, insert, update, delete on conexoes to {ROLE}")
    op.execute("alter table conexoes enable row level security")
    op.execute(
        """
        create policy "conexoes da minha organizacao" on conexoes
          for all using (organizacao_id in (select public.organizacoes_do_usuario()))
          with check (organizacao_id in (select public.organizacoes_do_usuario()))
        """
    )


def downgrade() -> None:
    op.drop_table("conexoes")
