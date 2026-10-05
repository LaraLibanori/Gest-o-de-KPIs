-- Taxas de acerto da classificação, sobre as colunas que o usuário confirmou.
select
  c.nome as conexao,
  count(*) as confirmadas,
  round(100.0 * count(*) filter (where k.papel_regra = k.papel) / count(*), 1)
    as acerto_regra,
  count(k.papel_modelo) as com_sugestao,
  round(
    100.0 * count(*) filter (where k.papel_modelo = k.papel)
      / nullif(count(k.papel_modelo), 0),
    1
  ) as acerto_modelo
from catalogo_campos k
join conexoes c on c.id = k.conexao_id
where k.confirmado and k.formula is null and k.papel_regra is not null
group by c.nome
order by c.nome;
