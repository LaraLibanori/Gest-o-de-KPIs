from dataclasses import dataclass

from app.calculo import _conta, _recorte, _serie


@dataclass
class Indicador:
    agregacao: str = "soma"
    coluna: str | None = "valor_total"
    tempo: str | None = None
    periodo: str | None = None
    dimensao: str | None = None
    grafico: str = "numero"


class ConexaoFalsa:
    def __init__(self):
        self.sql = None

    async def fetch(self, sql):
        self.sql = sql
        return []


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


async def test_numero_nao_consulta_a_serie():
    conexao = ConexaoFalsa()
    indicador = Indicador(dimensao="categoria", grafico="numero")
    assert await _serie(conexao, '"e"."v"', "", indicador) == []
    assert conexao.sql is None


async def test_linha_agrupa_pelo_balde_do_periodo():
    conexao = ConexaoFalsa()
    await _serie(
        conexao,
        '"e"."v"',
        "",
        Indicador(grafico="linha", tempo="vendida_em", periodo="ultimos_90_dias"),
    )
    assert "date_trunc('week', \"vendida_em\")" in conexao.sql


async def test_periodo_aberto_agrupa_por_mes():
    conexao = ConexaoFalsa()
    await _serie(
        conexao,
        '"e"."v"',
        "",
        Indicador(grafico="linha", tempo="vendida_em", periodo="sempre"),
    )
    assert "date_trunc('month'" in conexao.sql


async def test_quebra_cita_a_dimensao():
    conexao = ConexaoFalsa()
    await _serie(
        conexao,
        '"e"."v"',
        "",
        Indicador(dimensao='cat"; drop table v; --', grafico="barra"),
    )
    assert '"cat""; drop table v; --"' in conexao.sql
    assert "limit 12" in conexao.sql
