-- Base de exemplo, no papel de banco do cliente. Rode com `make exemplo`.
-- A senha vem de DEMO_LEITOR_PASSWORD, não fica aqui.

create schema if not exists exemplo;

drop table if exists exemplo.vendas;
create table exemplo.vendas (
  id              bigserial primary key,
  pedido_id       bigint not null,
  produto         text not null,
  categoria       text not null,
  regiao          text not null,
  canal           text not null,
  quantidade      integer not null,
  valor_unitario  numeric(12, 2) not null,
  valor_total     numeric(12, 2) not null,
  vendida_em      date not null
);

insert into exemplo.vendas
  (pedido_id, produto, categoria, regiao, canal, quantidade,
   valor_unitario, valor_total, vendida_em)
select
  1000 + i / 3,
  'Produto ' || lpad((i % 180)::text, 3, '0'),
  (array['Eletrônicos', 'Móveis', 'Acessórios', 'Ferramentas'])[1 + i % 4],
  (array['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'])[1 + i % 5],
  (array['Loja física', 'Site', 'Marketplace'])[1 + i % 3],
  q.quantidade,
  q.preco,
  round(q.quantidade * q.preco, 2),
  current_date - (i % 730)
from generate_series(1, 6000) i
cross join lateral (
  select 1 + i % 12 as quantidade,
         round((20 + (i * 7 % 4800) / 10.0)::numeric, 2) as preco
) q;

create index on exemplo.vendas (vendida_em);
analyze exemplo.vendas;

-- Usuário de leitura, como um cliente entregaria o acesso.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'demo_leitor') then
    create role demo_leitor login;
  end if;
end
$$;

alter role demo_leitor with password :'senha';
revoke all on schema public from demo_leitor;
grant usage on schema exemplo to demo_leitor;
grant select on all tables in schema exemplo to demo_leitor;
