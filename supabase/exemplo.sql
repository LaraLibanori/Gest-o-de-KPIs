-- Base de exemplo, no papel de banco do cliente. Rode com `make exemplo`.
-- A senha vem de DEMO_LEITOR_PASSWORD, não fica aqui.

create schema if not exists exemplo;

-- Deixa a geração repetível: rodar duas vezes dá a mesma base.
select setseed(0.42);

drop table if exists exemplo.vendas;
create table exemplo.vendas (
  id               bigserial primary key,
  pedido_id        bigint not null,
  cliente_id       bigint not null,
  produto          text not null,
  categoria        text not null,
  regiao           text not null,
  canal            text not null,
  vendedor         text not null,
  forma_pagamento  text not null,
  quantidade       integer not null,
  valor_unitario   numeric(12, 2) not null,
  custo_unitario   numeric(12, 2) not null,
  desconto         numeric(12, 2) not null,
  valor_total      numeric(12, 2) not null,
  vendida_em       date not null
);

-- Uma linha por venda: é o que faz "ticket médio" ser a média de valor_total.
insert into exemplo.vendas
  (pedido_id, cliente_id, produto, categoria, regiao, canal, vendedor,
   forma_pagamento, quantidade, valor_unitario, custo_unitario, desconto,
   valor_total, vendida_em)
with dias as (
  select d::date as dia,
         (current_date - d::date) as idade,
         extract(month from d) as mes,
         extract(dow from d) as semana
  from generate_series(current_date - 729, current_date, interval '1 day') d
),
volume as (
  select dia,
         greatest(1, round(
           20
           * (1 + 0.45 * (730 - idade) / 730.0)
           * (case when mes in (11, 12) then 1.7
                   when mes in (1, 2) then 0.75
                   else 1 end)
           * (case when semana = 0 then 0.55 else 1 end)
           * (0.7 + random() * 0.6)
         ))::int as vendas
  from dias
),
linhas as (
  select row_number() over (order by v.dia, g) as n,
         v.dia,
         random() as r_cat,
         random() as r_reg,
         random() as r_can,
         random() as r_pag,
         random() as r_cli,
         random() as r_preco,
         random() as r_qtd,
         random() as r_desc,
         random() as r_margem,
         random() as r_vend,
         random() as r_prod
  from volume v
  cross join generate_series(1, v.vendas) g
),
atributos as (
  select
    n,
    dia,
    1 + floor(12000 * power(r_cli, 1.6))::bigint as cliente_id,
    case when r_cat < 0.30 then 'Eletrônicos'
         when r_cat < 0.55 then 'Móveis'
         when r_cat < 0.85 then 'Acessórios'
         else 'Ferramentas' end as categoria,
    case when r_reg < 0.44 then 'Sudeste'
         when r_reg < 0.64 then 'Sul'
         when r_reg < 0.82 then 'Nordeste'
         when r_reg < 0.93 then 'Centro-Oeste'
         else 'Norte' end as regiao,
    case when r_can < 0.45 then 'Loja física'
         when r_can < 0.80 then 'Site'
         else 'Marketplace' end as canal,
    case when r_pag < 0.42 then 'Cartão de crédito'
         when r_pag < 0.68 then 'Pix'
         when r_pag < 0.86 then 'Boleto'
         else 'Dinheiro' end as forma_pagamento,
    (array['Ana Souza', 'Bruno Lima', 'Carla Dias', 'Diego Alves',
           'Elisa Rocha', 'Felipe Nunes'])[1 + floor(r_vend * 6)::int] as vendedor,
    r_preco, r_qtd, r_desc, r_margem, r_prod
  from linhas
)
select
  100000 + n,
  cliente_id,
  categoria || ' ' || lpad((1 + floor(r_prod * 40)::int)::text, 2, '0') as produto,
  categoria,
  regiao,
  canal,
  vendedor,
  forma_pagamento,
  qtd,
  preco,
  round((preco * (0.45 + r_margem * 0.25))::numeric, 2),
  desconto,
  round(qtd * preco - desconto, 2),
  dia
from atributos
cross join lateral (
  select
    case when categoria = 'Eletrônicos' then round((300 + r_preco * 3700)::numeric, 2)
         when categoria = 'Móveis'      then round((200 + r_preco * 2300)::numeric, 2)
         when categoria = 'Acessórios'  then round((15 + r_preco * 185)::numeric, 2)
         else round((40 + r_preco * 560)::numeric, 2) end as preco,
    case when r_qtd < 0.55 then 1
         when r_qtd < 0.82 then 2
         when r_qtd < 0.94 then 3
         else 4 + floor((r_qtd - 0.94) * 100)::int end as qtd
) p
cross join lateral (
  select case when r_desc < 0.72 then 0
              else round((qtd * preco * (0.05 + r_desc * 0.12))::numeric, 2) end as desconto
) d;

create index on exemplo.vendas (vendida_em);
create index on exemplo.vendas (cliente_id);
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
