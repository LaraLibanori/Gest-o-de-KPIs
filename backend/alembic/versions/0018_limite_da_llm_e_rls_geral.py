"""limite diario de chamadas a llm e rls em todas as tabelas"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

ROLE = "kpi_api"


def upgrade() -> None:
    op.execute("alter table alembic_version enable row level security")

    op.execute(
        """
        create table uso_llm (
          id bigserial primary key,
          usuario_id uuid not null,
          criado_em timestamptz not null default now()
        )
        """
    )
    op.execute("create index uso_llm_criado_em on uso_llm (criado_em)")
    op.execute("alter table uso_llm enable row level security")

    # So esta funcao enxerga o uso de todos; a tabela fica fechada para o role.
    op.execute(
        """
        create function public.reservar_llm(p_por_usuario int, p_total int)
        returns text language plpgsql security definer set search_path = public as $$
        declare
          v_usuario uuid := public.usuario_atual();
        begin
          delete from uso_llm where criado_em < now() - interval '2 days';
          if (select count(*) from uso_llm
              where usuario_id = v_usuario
                and criado_em > now() - interval '1 day') >= p_por_usuario then
            return 'usuario';
          end if;
          if (select count(*) from uso_llm
              where criado_em > now() - interval '1 day') >= p_total then
            return 'total';
          end if;
          insert into uso_llm (usuario_id) values (v_usuario);
          return 'ok';
        end $$
        """
    )
    op.execute("revoke execute on function public.reservar_llm(int, int) from public")
    op.execute(f"grant execute on function public.reservar_llm(int, int) to {ROLE}")
    # O Supabase concede execute a esses papeis por padrao, fora do "public".
    op.execute(
        """
        do $$
        declare papel text;
        begin
          foreach papel in array array['anon', 'authenticated'] loop
            if exists (select 1 from pg_roles where rolname = papel) then
              execute format(
                'revoke all on function public.reservar_llm(int, int) from %I', papel
              );
            end if;
          end loop;
        end $$
        """
    )


def downgrade() -> None:
    op.execute("drop function public.reservar_llm(int, int)")
    op.execute("drop table uso_llm")
