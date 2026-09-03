-- Rode uma vez no SQL Editor do Supabase.

create table dashboards (
  id         uuid primary key default gen_random_uuid(),
  owner_id   uuid not null references auth.users (id) on delete cascade,
  nome       text not null,
  criado_em  timestamptz not null default now()
);

create table indicadores (
  id            uuid primary key default gen_random_uuid(),
  dashboard_id  uuid not null references dashboards (id) on delete cascade,
  nome          text not null,
  fonte         text not null,
  coluna        text,
  agregacao     text not null check (agregacao in ('count', 'sum', 'avg', 'min', 'max')),
  criado_em     timestamptz not null default now()
);

-- Tabela de exemplo, é sobre ela que os indicadores são calculados.
create table vendas (
  id          bigserial primary key,
  owner_id    uuid not null references auth.users (id) on delete cascade,
  produto     text not null,
  categoria   text not null,
  quantidade  integer not null,
  valor       numeric(12, 2) not null,
  vendida_em  date not null default current_date
);

create index on dashboards (owner_id);
create index on indicadores (dashboard_id);
create index on vendas (owner_id);

-- RLS protege o acesso direto pelo navegador. A API conecta como postgres e
-- não passa por aqui, por isso lá toda query também filtra por owner_id.
alter table dashboards  enable row level security;
alter table indicadores enable row level security;
alter table vendas      enable row level security;

create policy "dono do dashboard" on dashboards
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create policy "dono das vendas" on vendas
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create policy "indicador segue o dashboard" on indicadores
  for all using (
    exists (
      select 1 from dashboards d
      where d.id = indicadores.dashboard_id and d.owner_id = auth.uid()
    )
  ) with check (
    exists (
      select 1 from dashboards d
      where d.id = indicadores.dashboard_id and d.owner_id = auth.uid()
    )
  );
