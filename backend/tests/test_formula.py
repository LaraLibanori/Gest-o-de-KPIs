import pytest

from app.formula import FormulaInvalida, analisar

COLUNAS = {"valor_total", "custo", "quantidade"}


def sql(formula: str) -> str:
    return analisar(formula, COLUNAS, COLUNAS)[0]


def test_divisao_protege_o_divisor():
    assert sql("valor_total / quantidade") == (
        '("valor_total" / nullif(("quantidade")::numeric, 0))'
    )


def test_margem_usa_so_colunas_conhecidas():
    _, usadas = analisar("valor_total - custo * quantidade", COLUNAS, COLUNAS)
    assert usadas == COLUNAS


@pytest.mark.parametrize(
    "formula",
    [
        "valor_total; drop table vendas",
        "valor_total + (select 1)",
        "pg_sleep(10) + valor_total",
        "valor_total -- resto",
        "valor_total >= 1",
        "case when custo > 1 then 1 end",
        "outra_coluna + 1",
    ],
)
def test_recusa_o_que_nao_e_conta(formula):
    with pytest.raises(FormulaInvalida):
        sql(formula)
