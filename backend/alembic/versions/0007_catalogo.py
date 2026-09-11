"""catalogo"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

ROLE = "kpi_api"

ETAPAS = "('tabela', 'negocio', 'catalogo', 'pronta')"
PAPEIS = "('metrica', 'dimensao', 'tempo', 'ignorar')"


def upgrade() -> None:
    # As conexoes que ja existem foram criadas antes do assistente.
    op.execute(
        f"alter table conexoes add column etapa text not null default 'pronta'"
        f" check (etapa in {ETAPAS})"
    )
    op.add_column("conexoes", sa.Column("descricao_negocio", sa.Text(), nullable=True))
    op.add_column("conexoes", sa.Column("tabela_tipo", sa.Text(), nullable=True))

    op.create_table(
        "catalogo_campos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conexao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coluna", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("cardinalidade", sa.BigInteger(), nullable=True),
        sa.Column("papel", sa.Text(), nullable=False),
        sa.Column("rotulo", sa.Text(), nullable=True),
        sa.Column("confirmado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.CheckConstraint(f"papel in {PAPEIS}", name="catalogo_campos_papel_check"),
        sa.ForeignKeyConstraint(["conexao_id"], ["conexoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "create unique index catalogo_campos_unico on catalogo_campos (conexao_id, coluna)"
    )

    op.execute(f"grant select, insert, update, delete on catalogo_campos to {ROLE}")
    op.execute("alter table catalogo_campos enable row level security")
    # A policy de conexoes ja filtra o subselect por organizacao.
    op.execute(
        """
        create policy "catalogo da minha conexao" on catalogo_campos
          for all using (conexao_id in (select id from conexoes))
          with check (conexao_id in (select id from conexoes))
        """
    )


def downgrade() -> None:
    op.drop_table("catalogo_campos")
    op.drop_column("conexoes", "tabela_tipo")
    op.drop_column("conexoes", "descricao_negocio")
    op.drop_column("conexoes", "etapa")
