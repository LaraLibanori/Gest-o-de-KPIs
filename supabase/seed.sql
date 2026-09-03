-- Dados de exemplo. Rode depois de criar a conta, trocando o e-mail.
insert into vendas (owner_id, produto, categoria, quantidade, valor, vendida_em)
select
  u.id,
  v.produto,
  v.categoria,
  v.quantidade,
  v.valor,
  current_date - v.dias
from auth.users u
cross join (values
  ('Notebook',  'Eletrônicos', 2, 7400.00, 1),
  ('Monitor',   'Eletrônicos', 5, 6250.00, 3),
  ('Cadeira',   'Móveis',      3, 2100.00, 6),
  ('Mesa',      'Móveis',      1,  890.00, 9),
  ('Headset',   'Acessórios',  8, 1920.00, 12),
  ('Teclado',   'Acessórios', 12, 2640.00, 15)
) as v (produto, categoria, quantidade, valor, dias)
where u.email = 'troque@pelo-seu-email.com';
