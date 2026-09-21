"""tipo de grafico"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

GRAFICOS = "('numero', 'barra', 'linha', 'pizza', 'tabela')"


def upgrade() -> None:
    op.execute(
        f"alter table indicadores add column grafico text not null default 'numero'"
        f" check (grafico in {GRAFICOS})"
    )
    op.execute("update indicadores set grafico = 'barra' where dimensao is not null")


def downgrade() -> None:
    op.drop_column("indicadores", "grafico")
