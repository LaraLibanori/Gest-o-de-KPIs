-- Protege a conta de demonstração: ela fica como "membro" (não "dono") em
-- toda organização de que participa, então pode ver conexões, indicadores e
-- dashboards, mas não cria, edita nem apaga nada.
--
-- Rode no SQL Editor do Supabase sempre que quiser conferir ou reaplicar a
-- proteção (é seguro rodar de novo: é um UPDATE idempotente). Troque o
-- e-mail abaixo se a conta de demonstração usar outro.

update organizacao_membros m
set papel = 'membro'
from auth.users u
where m.usuario_id = u.id
  and u.email = 'admin@kpibuilder.app'
  and m.papel <> 'membro';

-- Confirma o resultado: a conta de demonstração não deve aparecer aqui.
select o.nome, m.papel
from organizacao_membros m
join auth.users u on u.id = m.usuario_id
join organizacoes o on o.id = m.organizacao_id
where u.email = 'admin@kpibuilder.app';
