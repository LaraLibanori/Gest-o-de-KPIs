from dataclasses import dataclass

from app.calculo import _conta, _recorte


@dataclass
class Indicador:
    agregacao: str = "soma"
    coluna: str | None = "valor_total"
    tempo: str | None = None
    periodo: str | None = None


def test_nome_de_coluna_e_sempre_citado():
    sql = _conta(Indicador(coluna='valor"; drop table vendas; --'))
    assert sql == 'sum("valor""; drop table vendas; --")'


def test_contagem_nao_precisa_de_coluna():
    assert _conta(Indicador(agregacao="contagem", coluna=None)) == "count(*)"


def test_recorte_exige_campo_de_tempo():
    assert _recorte(Indicador(periodo="ultimos_30_dias", tempo=None)) == ""


def test_recorte_ignora_periodo_aberto():
    assert _recorte(Indicador(periodo="sempre", tempo="vendida_em")) == ""


def test_recorte_monta_o_filtro():
    sql = _recorte(Indicador(periodo="ultimos_30_dias", tempo="vendida_em"))
    assert sql == ' where "vendida_em" >= current_date - 30'
