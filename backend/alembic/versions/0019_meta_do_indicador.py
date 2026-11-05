"""meta mensal do indicador"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("indicadores", sa.Column("meta", sa.Numeric(), nullable=True))
    op.create_check_constraint("indicadores_meta_check", "indicadores", "meta >= 0")


def downgrade() -> None:
    op.drop_constraint("indicadores_meta_check", "indicadores")
    op.drop_column("indicadores", "meta")
