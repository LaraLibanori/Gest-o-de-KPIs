-- Dados de exemplo. Rode depois de criar a conta, trocando o e-mail.
-- A estrutura do banco vem das migrations: `make migrar`.
with nova as (
  insert into organizacoes (nome, criada_por)
  select 'Empresa Exemplo', u.id
  from auth.users u
  where u.email = 'troque@pelo-seu-email.com'
  returning id, criada_por
)
insert into organizacao_membros (organizacao_id, usuario_id, papel)
select id, criada_por, 'dono' from nova;
