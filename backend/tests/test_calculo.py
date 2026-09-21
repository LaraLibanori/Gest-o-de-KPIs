from dataclasses import dataclass

import asyncpg

from app.calculo import (
    CAIU,
    SEM_CAMPO,
    SEM_COLUNA,
    SEM_NUMERO,
    _conta,
    _recorte,
    _serie,
    calcular,
)


@dataclass
class Indicador:
    id: str = "1"
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


class ConexaoContada:
    def __init__(self, quebrar="", erro=None, texto=False):
        self.quebrar = quebrar
        self.erro = erro or asyncpg.UndefinedColumnError("column does not exist")
        self.texto = texto
        self.selects = []

    def _ver(self, sql):
        if sql.startswith("select"):
            self.selects.append(sql)
        if self.quebrar and self.quebrar in sql:
            raise self.erro

    async def execute(self, sql):
        self._ver(sql)

    async def fetchrow(self, sql):
        self._ver(sql)
        bruto = "texto" if self.texto else 1
        return {f"v{n}": bruto for n in range(sql.count(" as v"))}

    async def fetchval(self, sql):
        self._ver(sql)
        return 1

    async def fetch(self, sql):
        self._ver(sql)
        return []


async def test_mesmo_recorte_vai_num_select_so():
    conexao = ConexaoContada()
    painel = [
        Indicador(id="a", periodo="ultimos_30_dias", tempo="vendida_em"),
        Indicador(
            id="b", agregacao="media", periodo="ultimos_30_dias", tempo="vendida_em"
        ),
    ]
    await calcular(conexao, "exemplo.vendas", painel)
    assert len(conexao.selects) == 1


async def test_recortes_diferentes_vao_em_selects_separados():
    conexao = ConexaoContada()
    painel = [
        Indicador(id="a", periodo="ultimos_7_dias", tempo="vendida_em"),
        Indicador(id="b", periodo="ano_atual", tempo="vendida_em"),
    ]
    await calcular(conexao, "exemplo.vendas", painel)
    assert len(conexao.selects) == 2


async def test_coluna_que_sumiu_nao_leva_o_lote_junto():
    conexao = ConexaoContada(quebrar="sumiu")
    painel = [Indicador(id="a"), Indicador(id="b", coluna="sumiu")]
    resultado = await calcular(conexao, "exemplo.vendas", painel)
    assert resultado["a"]["valor"] == 1
    assert resultado["b"]["erro"] == SEM_COLUNA


async def test_indicador_sem_campo_nem_consulta():
    conexao = ConexaoContada()
    resultado = await calcular(
        conexao, "exemplo.vendas", [Indicador(id="a", coluna=None)]
    )
    assert resultado["a"]["erro"] == SEM_CAMPO
    assert conexao.selects == []


async def test_texto_onde_esperava_numero_erra_so_um():
    conexao = ConexaoContada(texto=True)
    resultado = await calcular(conexao, "exemplo.vendas", [Indicador(id="a")])
    assert resultado["a"]["erro"] == SEM_NUMERO


async def test_conexao_caida_nao_refaz_um_por_um():
    conexao = ConexaoContada(
        quebrar="select", erro=asyncpg.ConnectionDoesNotExistError("caiu")
    )
    painel = [Indicador(id="a"), Indicador(id="b"), Indicador(id="c")]
    resultado = await calcular(conexao, "exemplo.vendas", painel)
    assert len(conexao.selects) == 1
    assert all(resultado[i]["erro"] == CAIU for i in "abc")
