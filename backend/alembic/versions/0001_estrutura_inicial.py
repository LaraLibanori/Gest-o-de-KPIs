"""estrutura inicial"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

USUARIO = "auth.users.id"


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], [USUARIO], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboards_owner_id", "dashboards", ["owner_id"])

    op.create_table(
        "indicadores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dashboard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=False),
        sa.Column("coluna", sa.Text(), nullable=True),
        sa.Column("agregacao", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "agregacao in ('count', 'sum', 'avg', 'min', 'max')",
            name="indicadores_agregacao_check",
        ),
        sa.ForeignKeyConstraint(
            ["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indicadores_dashboard_id", "indicadores", ["dashboard_id"])

    op.create_table(
        "vendas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("produto", sa.Text(), nullable=False),
        sa.Column("categoria", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "vendida_em",
            sa.Date(),
            server_default=sa.text("current_date"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], [USUARIO], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendas_owner_id", "vendas", ["owner_id"])

    # RLS protege o acesso pelo navegador; a API filtra por owner_id.
    for tabela in ("dashboards", "indicadores", "vendas"):
        op.execute(f"alter table {tabela} enable row level security")

    op.execute(
        """
        create policy "dono do dashboard" on dashboards
          for all using (owner_id = auth.uid()) with check (owner_id = auth.uid())
        """
    )
    op.execute(
        """
        create policy "dono das vendas" on vendas
          for all using (owner_id = auth.uid()) with check (owner_id = auth.uid())
        """
    )
    op.execute(
        """
        create policy "indicador segue o dashboard" on indicadores
          for all using (
            exists (
              select 1 from dashboards d
              where d.id = indicadores.dashboard_id and d.owner_id = auth.uid()
            )
          ) with check (
            exists (
              select 1 from dashboards d
              where d.id = indicadores.dashboard_id and d.owner_id = auth.uid()
            )
          )
        """
    )


def downgrade() -> None:
    op.drop_table("vendas")
    op.drop_table("indicadores")
    op.drop_table("dashboards")
