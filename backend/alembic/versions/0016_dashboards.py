"""dashboards da organizacao"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "organizacao_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizacoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "criado_por",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organizacao_id", "nome", name="dashboards_nome_unico"),
    )
    op.create_index("dashboards_organizacao", "dashboards", ["organizacao_id"])

    op.create_table(
        "dashboard_indicadores",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "dashboard_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dashboards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "indicador_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("indicadores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "dashboard_id", "indicador_id", name="dashboard_indicadores_unico"
        ),
    )
    op.create_index(
        "dashboard_indicadores_dashboard",
        "dashboard_indicadores",
        ["dashboard_id"],
    )


def downgrade() -> None:
    op.drop_index("dashboard_indicadores_dashboard", table_name="dashboard_indicadores")
    op.drop_table("dashboard_indicadores")
    op.drop_index("dashboards_organizacao", table_name="dashboards")
    op.drop_table("dashboards")
