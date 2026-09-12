"""afina pistas"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# Pista com palavra generica empatava com a coluna errada: "identificador do
# cliente" casava tanto com cliente_id quanto com id.
TROCAS = [
    ("identificador do ", ""),
    ("valor da venda", "valor total da venda"),
    ("valor do pedido", "valor total do pedido"),
    ("valor do serviço", "valor total do serviço"),
    ("valor da conta", "valor total da conta"),
    ("valor do procedimento", "valor total do procedimento"),
]


def upgrade() -> None:
    for velho, novo in TROCAS:
        op.execute(
            f"update segmento_kpis set pista = replace(pista, '{velho}', '{novo}')"
            f" where pista like '%{velho}%'"
        )


def downgrade() -> None:
    for velho, novo in reversed(TROCAS):
        if not velho:
            continue
        op.execute(
            f"update segmento_kpis set pista = replace(pista, '{novo}', '{velho}')"
            f" where pista like '%{novo}%'"
        )
