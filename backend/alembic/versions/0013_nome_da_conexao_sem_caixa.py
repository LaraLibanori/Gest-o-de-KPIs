"""nome da conexao sem caixa"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        do $$
        declare conflito text;
        begin
          select string_agg(format('%s (org %s)', nome, organizacao_id), ', ')
            into conflito
            from (
              select organizacao_id, min(nome) as nome
                from conexoes
               group by organizacao_id, lower(nome)
              having count(*) > 1
            ) duplicados;
          if conflito is not null then
            raise exception
              'renomeie antes estas conexões, que só diferem em maiúscula/minúscula: %',
              conflito;
          end if;
        end;
        $$
        """
    )
    op.execute("drop index if exists conexoes_nome_unico")
    op.execute(
        "create unique index conexoes_nome_unico on conexoes (organizacao_id, lower(nome))"
    )


def downgrade() -> None:
    op.execute("drop index if exists conexoes_nome_unico")
    op.execute(
        "create unique index conexoes_nome_unico on conexoes (organizacao_id, nome)"
    )
