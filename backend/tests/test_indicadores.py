from dataclasses import dataclass

from app.indicadores import casar, por_regra


@dataclass
class Campo:
    coluna: str
    tipo: str
    papel: str
    rotulo: str
    ordem: int


@dataclass
class Kpi:
    nome: str
    pista: str | None
    agregacao: str


VENDAS = [
    Campo("id", "bigint", "ignorar", "Identificador", 1),
    Campo("cliente_id", "bigint", "ignorar", "Cliente", 2),
    Campo("categoria", "text", "dimensao", "Categoria", 3),
    Campo("quantidade", "integer", "metrica", "Quantidade vendida", 4),
    Campo("valor_unitario", "numeric", "metrica", "Valor unitário", 5),
    Campo("valor_total", "numeric", "metrica", "Valor total", 6),
    Campo("vendida_em", "date", "tempo", "Data da venda", 7),
]


def test_regra_entrega_cinco_sem_llm():
    assert len(por_regra(VENDAS)) == 5


def test_regra_nao_soma_preco_unitario():
    somas = [i["coluna"] for i in por_regra(VENDAS) if i["agregacao"] == "soma"]
    assert "valor_unitario" not in somas
    assert "valor_total" in somas


def test_contar_distintos_aceita_identificador():
    kpi = Kpi("Clientes atendidos", "cliente", "distintos")
    assert casar(kpi, VENDAS)["coluna"] == "cliente_id"


def test_match_ambiguo_vira_escolha():
    kpi = Kpi("Receita", "valor", "soma")
    resultado = casar(kpi, VENDAS)
    assert resultado["situacao"] == "escolher"
    assert resultado["coluna"] is None


def test_coluna_que_nao_existe_e_impossivel():
    sem_metrica = [c for c in VENDAS if c.papel != "metrica"]
    kpi = Kpi("Receita", "valor total da venda", "soma")
    assert casar(kpi, sem_metrica)["situacao"] == "impossivel"
