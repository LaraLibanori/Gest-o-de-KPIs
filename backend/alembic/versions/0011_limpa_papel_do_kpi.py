"""limpa papel do kpi"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("segmento_kpis", "papel")


def downgrade() -> None:
    op.add_column("segmento_kpis", sa.Column("papel", sa.Text(), nullable=True))
