"""email normalizado"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("update perfis set email = lower(email) where email <> lower(email)")
    op.execute("create unique index perfis_email_unico on perfis (lower(email))")

    # O convite procura o e-mail em minusculo, entao o trigger tem que gravar assim.
    op.execute(
        """
        create or replace function public.criar_perfil() returns trigger
        language plpgsql security definer set search_path = public as $$
        begin
          insert into perfis (id, email) values (new.id, lower(new.email))
          on conflict (id) do nothing;
          return new;
        end;
        $$
        """
    )


def downgrade() -> None:
    op.execute("drop index if exists perfis_email_unico")
    op.execute(
        """
        create or replace function public.criar_perfil() returns trigger
        language plpgsql security definer set search_path = public as $$
        begin
          insert into perfis (id, email) values (new.id, new.email)
          on conflict (id) do nothing;
          return new;
        end;
        $$
        """
    )
