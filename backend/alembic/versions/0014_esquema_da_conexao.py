"""esquema da conexao"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conexoes", sa.Column("esquema", sa.Text(), nullable=True))
    op.create_index("conexoes_esquema", "conexoes", ["esquema"])


def downgrade() -> None:
    op.drop_index("conexoes_esquema", table_name="conexoes")
    op.drop_column("conexoes", "esquema")
