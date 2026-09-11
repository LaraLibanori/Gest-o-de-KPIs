"""ajusta indicadores"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

ROLE = "kpi_api"

REFERENCIA = ("segmentos", "segmento_kpis", "classificacoes")


def upgrade() -> None:
    # for all deixava a policy permitir escrita; so os grants seguravam.
    for tabela in REFERENCIA:
        op.execute(f'drop policy "leitura comum" on {tabela}')
        op.execute(f'create policy "leitura comum" on {tabela} for select using (true)')

    op.execute(
        'create policy "grava classificacao" on classificacoes'
        " for insert with check (true)"
    )
    # A pessoa pode trocar o segmento que foi sugerido, e a troca corrige o cache.
    op.execute(
        'create policy "corrige classificacao" on classificacoes'
        " for update using (true) with check (true)"
    )
    op.execute(f"grant update on classificacoes to {ROLE}")

    op.execute(
        'create policy "grava kpi do segmento" on segmento_kpis'
        " for insert with check (true)"
    )

    op.execute(
        "create unique index indicadores_nome_unico on indicadores (conexao_id, nome)"
    )


def downgrade() -> None:
    op.execute("drop index indicadores_nome_unico")
    op.execute('drop policy "grava kpi do segmento" on segmento_kpis')
    op.execute(f"revoke update on classificacoes from {ROLE}")
    op.execute('drop policy "corrige classificacao" on classificacoes')
    op.execute('drop policy "grava classificacao" on classificacoes')
    for tabela in REFERENCIA:
        op.execute(f'drop policy "leitura comum" on {tabela}')
        op.execute(f'create policy "leitura comum" on {tabela} for all using (true)')
