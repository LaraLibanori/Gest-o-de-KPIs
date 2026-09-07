"""role da aplicacao"""

import os

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

ROLE = "kpi_api"
TABELAS = ("perfis", "organizacoes", "organizacao_membros")


def upgrade() -> None:
    senha = os.environ.get("KPI_APP_PASSWORD", "")
    if not senha:
        raise RuntimeError("defina KPI_APP_PASSWORD no backend/.env antes de migrar")
    if "'" in senha:
        raise RuntimeError("a senha do kpi_app não pode ter aspas simples")

    # A API deixa de conectar como postgres, que ignora RLS.
    op.execute(
        f"""
        do $$
        begin
          if not exists (select 1 from pg_roles where rolname = '{ROLE}') then
            create role {ROLE} login;
          end if;
        end
        $$
        """
    )
    op.execute(f"alter role {ROLE} with password '{senha}'")

    # nosuperuser e nobypassrls sao o padrao, e o postgres do Supabase nao tem
    # privilegio para declarar essas clausulas. Entao confere em vez de presumir.
    op.execute(
        f"""
        do $$
        begin
          if exists (
            select 1 from pg_roles
            where rolname = '{ROLE}' and (rolsuper or rolbypassrls)
          ) then
            raise exception '{ROLE} nao pode ter superuser nem bypassrls';
          end if;
        end
        $$
        """
    )

    op.execute(f"grant usage on schema public to {ROLE}")
    op.execute(f"grant select on perfis to {ROLE}")
    op.execute(f"grant select, insert, delete on organizacoes to {ROLE}")
    # update por causa do select ... for update que trava o ultimo dono.
    op.execute(f"grant select, insert, update, delete on organizacao_membros to {ROLE}")

    # O schema auth e do supabase_admin e o postgres nao consegue liberar acesso
    # a ele, entao as policies leem o usuario daqui em vez de auth.uid().
    op.execute(
        """
        create function public.usuario_atual() returns uuid
        language sql stable as $$
          select (
            nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
          )::uuid
        $$
        """
    )
    op.execute(
        """
        create or replace function public.organizacoes_do_usuario() returns setof uuid
        language sql security definer stable set search_path = public as $$
          select organizacao_id from organizacao_membros
          where usuario_id = public.usuario_atual()
        $$
        """
    )

    # O convite precisa achar quem ainda nao divide organizacao, e a policy de
    # perfis esconde essa linha. Esta funcao e a unica porta para isso.
    op.execute(
        """
        create function public.usuario_por_email(p_email text) returns uuid
        language sql security definer stable set search_path = public as $$
          select id from perfis where lower(email) = lower(p_email)
        $$
        """
    )
    op.execute("revoke execute on function public.usuario_por_email(text) from public")
    op.execute(f"grant execute on function public.usuario_por_email(text) to {ROLE}")

    op.execute(
        'drop policy if exists "perfil proprio ou de quem divide organizacao" on perfis'
    )
    op.execute(
        """
        create policy "perfil proprio ou de quem divide organizacao" on perfis
          for select using (
            id = public.usuario_atual()
            or exists (
              select 1 from organizacao_membros m
              where m.usuario_id = perfis.id
                and m.organizacao_id in (select public.organizacoes_do_usuario())
            )
          )
        """
    )

    op.execute('drop policy if exists "organizacao de que participo" on organizacoes')
    op.execute(
        """
        create policy "organizacao de que participo" on organizacoes
          for all using (id in (select public.organizacoes_do_usuario()))
          with check (criada_por = public.usuario_atual())
        """
    )

    # Criar organizacao pela API esbarra na RLS: o insert usa returning, que
    # tambem passa pela policy de select, e quem criou ainda nao e membro. Esta
    # funcao cria a organizacao e o dono de uma vez, garantindo que nenhuma
    # organizacao nasca sem dono.
    op.execute(
        """
        create function public.criar_organizacao(p_nome text) returns organizacoes
        language plpgsql security definer set search_path = public as $$
        declare
          nova organizacoes;
          dono uuid := public.usuario_atual();
        begin
          if dono is null then
            raise exception 'sem usuario na sessao';
          end if;
          insert into organizacoes (nome, criada_por) values (p_nome, dono)
          returning * into nova;
          insert into organizacao_membros (organizacao_id, usuario_id, papel)
          values (nova.id, dono, 'dono');
          return nova;
        end;
        $$
        """
    )
    op.execute("revoke execute on function public.criar_organizacao(text) from public")
    op.execute(f"grant execute on function public.criar_organizacao(text) to {ROLE}")


def downgrade() -> None:
    op.execute("drop function if exists public.usuario_por_email(text)")
    op.execute("drop function if exists public.criar_organizacao(text)")

    # Devolve as policies da 0002, que voltam a usar auth.uid().
    op.execute(
        'drop policy if exists "perfil proprio ou de quem divide organizacao" on perfis'
    )
    op.execute(
        """
        create policy "perfil proprio ou de quem divide organizacao" on perfis
          for select using (
            id = auth.uid()
            or exists (
              select 1 from organizacao_membros m
              where m.usuario_id = perfis.id
                and m.organizacao_id in (select public.organizacoes_do_usuario())
            )
          )
        """
    )
    op.execute('drop policy if exists "organizacao de que participo" on organizacoes')
    op.execute(
        """
        create policy "organizacao de que participo" on organizacoes
          for all using (id in (select public.organizacoes_do_usuario()))
          with check (criada_por = auth.uid())
        """
    )
    op.execute(
        """
        create or replace function public.organizacoes_do_usuario() returns setof uuid
        language sql security definer stable set search_path = public as $$
          select organizacao_id from organizacao_membros where usuario_id = auth.uid()
        $$
        """
    )
    op.execute("drop function if exists public.usuario_atual()")

    op.execute(
        f"revoke execute on function public.organizacoes_do_usuario() from {ROLE}"
    )
    for tabela in TABELAS:
        op.execute(f"revoke all on {tabela} from {ROLE}")
    op.execute(f"revoke usage on schema public from {ROLE}")
    # O role fica, sem nenhum privilegio. Dropar e recriar invalida a identidade
    # que o pooler do Supabase guarda em cache e derruba a conexao por um tempo.
