"""campo calculado"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalogo_campos", sa.Column("formula", sa.Text(), nullable=True))
    op.create_check_constraint(
        "catalogo_campos_formula_papel_check",
        "catalogo_campos",
        "formula is null or papel in ('metrica', 'dimensao')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "catalogo_campos_formula_papel_check", "catalogo_campos", type_="check"
    )
    op.drop_column("catalogo_campos", "formula")