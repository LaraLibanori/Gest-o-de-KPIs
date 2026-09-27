
create schema if not exists moda_loja_schema;

begin;

select setseed(0.73);

drop table if exists moda_loja_schema.vendas;
drop table if exists moda_loja_schema.produtos;

create table moda_loja_schema.produtos (
  sku          text primary key,
  marca        text not null,
  categoria    text not null,
  subcategoria text not null,
  tamanho      text not null,
  cor          text not null,
  preco_lista  numeric(10, 2) not null,
  custo        numeric(10, 2) not null,
  estoque      integer not null,
  ativo_desde  date not null
);

insert into moda_loja_schema.produtos
  (sku, marca, categoria, subcategoria, tamanho, cor, preco_lista, custo, estoque, ativo_desde)
values
  ('MOD-VER-001', 'Aurora',  'Vestidos',   'Midi',         'P',     'Preto',     289.90,  96.40, 42, date '2023-01-01'),
  ('MOD-VER-002', 'Aurora',  'Vestidos',   'Longo',        'M',     'Vinho',     349.90, 118.70, 28, date '2023-01-01'),
  ('MOD-CAM-001', 'Boreal',  'Camisas',    'Manga longa',  'G',     'Branco',    199.90,  62.10, 65, date '2023-02-01'),
  ('MOD-CAM-002', 'Boreal',  'Camisas',    'Manga curta',  'P',     'Listra',    149.90,  45.30, 71, date '2023-02-01'),
  ('MOD-CAL-001', 'Cerrado', 'Calçados',   'Tênis',        '40',    'Branco',    429.90, 158.20, 33, date '2023-03-01'),
  ('MOD-CAL-002', 'Cerrado', 'Calçados',   'Bota',         '38',    'Preto',     499.90, 189.40, 19, date '2023-09-01'),
  ('MOD-BOL-001', 'Duna',    'Boletas',    'Mala',         'M',     'Caramelo',  259.90,  88.60, 47, date '2023-01-01'),
  ('MOD-BOL-002', 'Duna',    'Boletas',    'Bolsa de mão', 'G',     'Preto',     229.90,  77.90, 52, date '2023-04-01'),
  ('MOD-ACD-001', 'Aurora',  'Acessórios', 'Bolsa',        'Único', 'Marrom',    319.90, 104.30, 26, date '2023-01-01'),
  ('MOD-ACD-002', 'Boreal',  'Acessórios', 'Cinto',        'M',     'Preto',      89.90,  24.70, 88, date '2023-01-01'),
  ('MOD-ACD-003', 'Duna',    'Acessórios', 'Lenço',        'Único', 'Estampado',  79.90,  19.80, 94, date '2023-05-01'),
  ('MOD-JOA-001', 'Cerrado', 'Jojias',     'Colar',        'Único', 'Ouro',      189.90,  58.40, 31, date '2023-06-01'),
  ('MOD-ROU-001', 'Aurora',  'Roupões',    'Plush',        'G',     'Cinza',     379.90, 141.20, 15, date '2023-10-01'),
  ('MOD-ROU-002', 'Boreal',  'Roupões',    'Cardigã',      'P',     'Areia',     299.90, 112.50, 22, date '2023-08-01');

create table moda_loja_schema.vendas (
  valor_total     numeric(12, 2) not null,
  valor_unitario  numeric(10, 2) not null,
  desconto        numeric(10, 2) not null,
  quantidade      integer not null,
  custo_total     numeric(12, 2) not null,
  id_pedido       bigint not null,
  id_cliente      bigint not null,
  data_venda      date not null,
  categoria       text not null,
  marca           text not null,
  tamanho         text not null,
  cor             text not null,
  canal           text not null,
  forma_pagamento text not null,
  regiao          text not null,
  uf              text not null,
  status_pedido   text not null
);

with dias as (
  select d::date as dia,
         extract(month from d) as mes,
         extract(dow from d) as semana
  from generate_series(current_date - 364, current_date, interval '1 day') d
),
volume as (
  select dia,
         extract(month from dia) as mes,
         extract(dow from dia) as semana,
         greatest(1, round(
           40
           * (1 + 0.30 * (dia - (current_date - 364)) / 364.0)
           * (case extract(month from dia)
                when 11 then 2.1 when 12 then 2.4 when 5 then 1.5
                when 1 then 0.65 when 2 then 0.8 else 1.0 end)
           * (case when extract(dow from dia) in (0, 6) then 1.25 else 0.92 end)
           * (0.75 + random() * 0.5)
         ))::int as itens
  from dias
),
pedidos as (
  select v.dia,
         row_number() over (order by v.dia, g.pedido) as pedido,
         1 + floor(random() * 4)::int as itens
  from volume v
  cross join lateral generate_series(
    1, greatest(1, floor(v.itens / 1.8)::int)
  ) as g(pedido)
),
linhas as (
  select p.dia,
         p.pedido,
         l.item,
         row_number() over (order by p.dia, p.pedido, l.item) as n
  from pedidos p
  cross join lateral generate_series(1, p.itens) as l(item)
),
sorteadas as (
  select li.*,
         pr.sku, pr.marca, pr.categoria, pr.tamanho, pr.cor,
         pr.preco_lista, pr.custo,
         greatest(1, 1 + floor(random() * 3)::int) as qtd,
         (case when random() < 0.34
               then round((pr.preco_lista * (0.05 + random() * 0.20))::numeric, 2)
               else 0 end) as desconto,
         random() as r_cli,
         random() as r_canal,
         random() as r_pag,
         random() as r_reg,
         random() as r_uf,
         random() as r_status
  from linhas li
  join moda_loja_schema.produtos pr on pr.sku = (
    select p2.sku
      from moda_loja_schema.produtos p2
     order by md5(p2.sku || li.n::text)
     limit 1
  )
)
insert into moda_loja_schema.vendas
  (valor_total, valor_unitario, desconto, quantidade, custo_total,
   id_pedido, id_cliente, data_venda, categoria, marca, tamanho, cor,
   canal, forma_pagamento, regiao, uf, status_pedido)
select
  greatest(1, round(s.qtd * s.preco_lista - s.desconto, 2)),
  s.preco_lista,
  s.desconto,
  s.qtd,
  round(s.qtd * s.custo, 2),
  500000 + s.pedido,
  1 + floor(12000 * power(s.r_cli, 1.7))::bigint,
  s.dia,
  s.categoria,
  s.marca,
  s.tamanho,
  s.cor,
  (case when s.r_canal < 0.46 then 'Site'
        when s.r_canal < 0.78 then 'App'
        when s.r_canal < 0.92 then 'Instagram'
        else 'Loja física' end),
  (case when s.r_pag < 0.38 then 'Pix'
        when s.r_pag < 0.66 then 'Cartão de crédito'
        when s.r_pag < 0.84 then 'Cartão de débito'
        when s.r_pag < 0.93 then 'Boleto'
        else 'Dinheiro' end),
  (case when s.r_reg < 0.42 then 'Sudeste'
        when s.r_reg < 0.63 then 'Sul'
        when s.r_reg < 0.82 then 'Nordeste'
        when s.r_reg < 0.93 then 'Centro-Oeste'
        else 'Norte' end),
  (array['SP','RJ','MG','PR','RS','SC','BA','PE','CE','GO','DF','AM','PA','PB','RN'])[
    1 + floor(s.r_uf * 15)::int
  ],
  (case when s.r_status < 0.06 then 'Cancelado'
        when s.r_status < 0.09 then 'Em trânsito'
        else 'Concluído' end)
from sorteadas s;

create index on moda_loja_schema.vendas (data_venda);
create index on moda_loja_schema.vendas (id_cliente);
create index on moda_loja_schema.vendas (categoria);
analyze moda_loja_schema.vendas;
analyze moda_loja_schema.produtos;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'demo_leitor') then
    create role demo_leitor login;
  end if;
end
$$;

alter role demo_leitor with password :'senha';
revoke all on schema public from demo_leitor;
grant usage on schema moda_loja_schema to demo_leitor;
grant select on all tables in schema moda_loja_schema to demo_leitor;
alter default privileges in schema moda_loja_schema grant select on tables to demo_leitor;

commit;
