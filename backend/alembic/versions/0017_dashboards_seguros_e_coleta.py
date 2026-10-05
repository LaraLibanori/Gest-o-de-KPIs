"""acesso dos dashboards, papeis do catalogo e fechamento da api rest"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

ROLE = "kpi_api"
TABELAS = (
    "perfis",
    "organizacoes",
    "organizacao_membros",
    "convites",
    "conexoes",
    "catalogo_campos",
    "segmentos",
    "segmento_kpis",
    "classificacoes",
    "indicadores",
    "dashboards",
    "dashboard_indicadores",
)


def upgrade() -> None:
    op.execute(f"grant select, insert, update, delete on dashboards to {ROLE}")
    op.execute(
        f"grant select, insert, update, delete on dashboard_indicadores to {ROLE}"
    )
    op.execute("alter table dashboards enable row level security")
    op.execute("alter table dashboard_indicadores enable row level security")
    op.execute(
        """
        create policy "dashboards da minha organizacao" on dashboards
          for all using (organizacao_id in (select public.organizacoes_do_usuario()))
          with check (organizacao_id in (select public.organizacoes_do_usuario()))
        """
    )
    op.execute(
        """
        create policy "indicadores do meu dashboard" on dashboard_indicadores
          for all using (dashboard_id in (select id from dashboards))
          with check (
            dashboard_id in (select id from dashboards)
            and indicador_id in (select id from indicadores)
          )
        """
    )

    op.add_column("catalogo_campos", sa.Column("papel_regra", sa.Text()))
    op.add_column("catalogo_campos", sa.Column("papel_modelo", sa.Text()))

    # O front so usa o Supabase para o login; as tabelas so a API deve alcancar.
    lista = ", ".join(TABELAS)
    op.execute(
        f"""
        do $$
        begin
          if exists (select 1 from pg_roles where rolname = 'anon') then
            revoke all on {lista} from anon;
            revoke execute on function public.usuario_por_email(text) from anon;
            revoke execute on function public.criar_organizacao(text) from anon;
          end if;
          if exists (select 1 from pg_roles where rolname = 'authenticated') then
            revoke all on {lista} from authenticated;
            revoke execute on function public.usuario_por_email(text) from authenticated;
            revoke execute on function public.criar_organizacao(text) from authenticated;
          end if;
        end $$
        """
    )


def downgrade() -> None:
    op.drop_column("catalogo_campos", "papel_modelo")
    op.drop_column("catalogo_campos", "papel_regra")
    op.execute('drop policy "indicadores do meu dashboard" on dashboard_indicadores')
    op.execute('drop policy "dashboards da minha organizacao" on dashboards')
    op.execute("alter table dashboard_indicadores disable row level security")
    op.execute("alter table dashboards disable row level security")
    op.execute(f"revoke all on dashboard_indicadores, dashboards from {ROLE}")
