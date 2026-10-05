from dataclasses import dataclass

import asyncpg

from app.calculo import (
    CAIU,
    SEM_CAMPO,
    SEM_COLUNA,
    SEM_NUMERO,
    _conta,
    _onde,
    calcular,
    compor,
    janela_de,
    variacao,
)


@dataclass
class Indicador:
    id: str = "1"
    agregacao: str = "soma"
    coluna: str | None = "valor_total"
    tempo: str | None = "vendida_em"
    dimensao: str | None = None
    periodo: str | None = "sempre"
    grafico: str = "numero"


class ConexaoFalsa:
    def __init__(self):
        self.sql = None

    async def fetch(self, sql, *args):
        self.sql = sql
        return []


def test_nome_de_coluna_e_sempre_citado():
    sql = _conta(Indicador(coluna='valor"; drop table vendas; --'))
    assert sql == 'sum("valor""; drop table vendas; --")'


def test_contagem_nao_precisa_de_coluna():
    assert _conta(Indicador(agregacao="contagem", coluna=None)) == "count(*)"


def test_janela_desconhecida_cai_no_padrao():
    assert janela_de("nao-existe") == janela_de("30d")
    assert janela_de(None) == janela_de("30d")


def test_recorte_exige_coluna_de_tempo():
    assert _onde(None, "current_date - 30") == ""
    assert _onde("vendida_em", "") == ""


def test_janela_tudo_nao_recorta():
    inicio, antes, _ = janela_de("tudo")
    assert inicio == "" and antes == ""


def test_filtro_cita_a_coluna():
    assert _onde("vendida_em", "current_date - 30") == (
        ' where "vendida_em" >= current_date - 30'
    )


def test_variacao_usa_base_absoluta():
    assert variacao(120, 100) == 20
    assert variacao(80, 100) == -20
    # Subir de -100 para 0 e subir 100%, nao descer.
    assert variacao(0, -100) == 100


def test_variacao_sem_base_nao_inventa_numero():
    assert variacao(100, 0) is None
    assert variacao(None, 100) is None
    assert variacao(100, None) is None


class ConexaoContada:
    def __init__(self, quebrar="", erro=None, texto=False, com_antes=True):
        self.quebrar = quebrar
        self.erro = erro or asyncpg.UndefinedColumnError("column does not exist")
        self.texto = texto
        self.com_antes = com_antes
        self.selects = []
        self.sql = None

    def _ver(self, sql):
        self.sql = sql
        if sql.startswith("select"):
            self.selects.append(sql)
        if self.quebrar and self.quebrar in sql:
            raise self.erro

    async def execute(self, sql):
        self._ver(sql)

    async def fetchrow(self, sql):
        self._ver(sql)
        bruto = "texto" if self.texto else 1
        if self.texto:
            return {"v0": bruto}
        if self.com_antes:
            return {"v0": 2, "a0": 1}
        return {"v0": 2}

    async def fetchval(self, sql):
        self._ver(sql)
        return 1

    async def fetch(self, sql):
        self._ver(sql)
        return []


async def test_agora_e_antes_viem_no_mesmo_select():
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "30d")
    valores = [s for s in conexao.selects if "filter" in s]
    assert len(valores) == 1
    # Com "filter (" a query nem roda, e o fallback por indicador perde a variacao.
    assert 'sum("valor_total") filter (where "vendida_em" >=' in valores[0]
    assert "current_date - 59" in valores[0]
    assert "current_date - 29" in valores[0]


async def test_janela_tudo_nao_pede_variacao():
    conexao = ConexaoContada()
    resultado = await calcular(conexao, "exemplo.vendas", [Indicador()], "tudo")
    assert not any("filter" in s for s in conexao.selects)
    assert resultado["1"]["anterior"] is None
    assert resultado["1"]["variacao"] is None


async def test_a_janela_anterior_nao_pode_vir_de_where_externo():
    # Com where externo na janela atual, a anterior vira recorte vazio e a variacao some.
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "30d")
    linha = next(s for s in conexao.selects if "filter" in s)
    assert " where " not in linha.split(" from ")[0].replace("filter (where ", "")


async def test_o_where_da_janela_vem_so_do_from():
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "90d")
    linha = next(s for s in conexao.selects if "filter" in s)
    dentro = linha.split("filter (where ")[1].split(")")[0]
    assert "where" not in dentro
    assert '"vendida_em" >= current_date - 179' in dentro


async def test_serie_agrupa_pelo_balde_da_janela():
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "90d")
    assert "date_trunc('week'" in conexao.sql


async def test_janela_curta_agrupa_por_dia():
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "7d")
    assert "date_trunc('day'" in conexao.sql


async def test_ano_agrupa_por_mes():
    conexao = ConexaoContada()
    await calcular(conexao, "exemplo.vendas", [Indicador()], "12m")
    assert "date_trunc('month'" in conexao.sql


async def test_coluna_que_sumiu_nao_leva_o_lote_junto():
    conexao = ConexaoContada(quebrar="sumiu")
    painel = [Indicador(id="a"), Indicador(id="b", coluna="sumiu")]
    resultado = await calcular(conexao, "exemplo.vendas", painel, "30d")
    # O lote inteiro falhou, entao cada um foi refeito e so o culpado became erro.
    assert resultado["a"]["valor"] is not None
    assert resultado["b"]["erro"] == SEM_COLUNA


async def test_indicador_sem_campo_nao_consulta():
    conexao = ConexaoContada()
    resultado = await calcular(
        conexao, "exemplo.vendas", [Indicador(id="a", coluna=None)], "30d"
    )
    assert resultado["a"]["erro"] == SEM_CAMPO
    assert conexao.selects == []


async def test_texto_onde_esperava_numero_erra_so_um():
    conexao = ConexaoContada(texto=True)
    resultado = await calcular(conexao, "exemplo.vendas", [Indicador(id="a")], "30d")
    assert resultado["a"]["erro"] == SEM_NUMERO


async def test_conexao_caida_nao_refaz_um_por_um():
    conexao = ConexaoContada(
        quebrar="select", erro=asyncpg.ConnectionDoesNotExistError("caiu")
    )
    painel = [Indicador(id="a"), Indicador(id="b"), Indicador(id="c")]
    resultado = await calcular(conexao, "exemplo.vendas", painel, "30d")
    assert len(conexao.selects) == 1
    assert all(resultado[i]["erro"] == CAIU for i in "abc")


class ComposicaoFalsa:
    def __init__(self):
        self.sql = None

    async def execute(self, sql):
        pass

    async def fetch(self, sql, *args):
        self.sql = sql
        return [
            {"rotulo": "Site", "valor": 46, "total": 81},
            {"rotulo": "App", "valor": 32, "total": 81},
            {"rotulo": None, "valor": 3, "total": 81},
        ]


async def test_composicao_cita_dimensao_e_ordena():
    conexao = ComposicaoFalsa()
    pontos, total = await compor(
        conexao,
        "exemplo.vendas",
        Indicador(agregacao="soma"),
        'canal"; drop table x; --',
        "30d",
    )
    assert "order by 2 desc" in conexao.sql
    assert 'canal""; drop table x; --' in conexao.sql
    assert pontos[2]["rotulo"] == "sem valor"
    assert total == 81


async def test_composicao_respeita_a_janela():
    conexao = ComposicaoFalsa()
    await compor(conexao, "exemplo.vendas", Indicador(), "canal", "90d")
    assert "current_date - 89" in conexao.sql
    assert "limit 10" in conexao.sql


async def test_resgate_usa_o_where_pronto_e_nao_o_filtro():
    # Passar o fragmento do filter no resgate daria syntax error.
    conexao = ConexaoContada(quebrar="sum(")
    await calcular(conexao, "exemplo.vendas", [Indicador()], "30d")
    resgatado = next(s for s in conexao.selects if "filter" not in s)
    assert resgatado == (
        'select sum("valor_total") from "exemplo"."vendas"'
        ' where "vendida_em" >= current_date - 29'
    )


async def test_indicador_sem_tempo_ignora_o_periodo():
    conexao = ConexaoContada()
    painel = [Indicador(id="com"), Indicador(id="sem", tempo=None)]
    resultado = await calcular(conexao, "exemplo.vendas", painel, "30d")
    assert resultado["sem"]["valor"] is not None
    assert resultado["sem"]["anterior"] is None
    assert resultado["sem"]["serie"] == []
    # O sem tempo conta a tabela toda: o select dele nao tem filtro nenhum.
    dele = next(
        s for s in conexao.selects if s.count("sum(") == 1 and "filter" not in s
    )
    assert "where" not in dele
