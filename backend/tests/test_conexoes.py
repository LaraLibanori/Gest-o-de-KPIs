import asyncpg
import pytest

from tests.conftest import criar_usuario

CONEXAO = {
    "nome": "Producao",
    "host": "db.exemplo.com",
    "porta": 5432,
    "banco": "vendas",
    "usuario": "leitor",
    "senha": "segredo-do-banco",
}


def com_nome(nome: str) -> dict:
    return {**CONEXAO, "nome": nome}


async def test_nome_repetido_na_mesma_organizacao_da_409(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        assert (
            await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)
        ).status_code == 201

        repetida = await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)
        assert repetida.status_code == 409
        # A mensagem precisa dizer qual nome travou, senao o usuario nao sabe o que mudar.
        assert "Producao" in repetida.json()["detail"]


async def test_nome_ignora_maiuscula_e_espaco(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)

        # O schema tira o espaco das pontas e a unicidade ignora a caixa.
        assert (
            await c.post(f"/organizacoes/{org}/conexoes", json=com_nome("  PRODUCAO  "))
        ).status_code == 409


async def test_o_indice_tambem_barra_casmo(cliente, admin):
    # A checagem do endpoint e so conveniencia: quem garante, sob concorrencia,
    # e o indice unico. Aqui o insert passa por fora da API de proposito.
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)
        dono = await admin.fetchval(
            "select criada_por from conexoes where organizacao_id = $1", org
        )

    with pytest.raises(asyncpg.UniqueViolationError):
        await admin.execute(
            "insert into conexoes (organizacao_id, nome, host, porta, banco, usuario,"
            " senha_cifrada, etapa, criada_por)"
            " values ($1, 'producao', 'h', 5432, 'b', 'u', 'c', 'tabela', $2)",
            org,
            dono,
        )


async def test_mesmo_nome_em_outras_organizacoes_pode(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        acme = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        outra = (await c.post("/organizacoes", json={"nome": "Beta"})).json()["id"]
        assert (
            await c.post(f"/organizacoes/{acme}/conexoes", json=CONEXAO)
        ).status_code == 201
        assert (
            await c.post(f"/organizacoes/{outra}/conexoes", json=CONEXAO)
        ).status_code == 201


async def test_descartar_apaga_tambem_catalogo_e_indicadores(cliente, admin):
    # E o que faz o "Cancelar" do assistente nao deixar rascunho para tras.
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        nova = (await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)).json()
        await admin.execute(
            "insert into catalogo_campos (conexao_id, coluna, tipo, papel, ordem)"
            " values ($1, 'valor_total', 'numeric', 'metrica', 0)",
            nova["id"],
        )
        await admin.execute(
            "insert into indicadores (conexao_id, nome, agregacao, origem, ordem)"
            " values ($1, 'Receita', 'soma', 'regra', 0)",
            nova["id"],
        )

        assert (
            await c.delete(f"/organizacoes/{org}/conexoes/{nova['id']}")
        ).status_code == 204
        assert (await c.get(f"/organizacoes/{org}/conexoes")).json() == []

    assert (
        await admin.fetchval(
            "select count(*) from catalogo_campos where conexao_id = $1", nova["id"]
        )
        == 0
    )
    assert (
        await admin.fetchval(
            "select count(*) from indicadores where conexao_id = $1", nova["id"]
        )
        == 0
    )


async def test_nao_da_para_concluir_sem_indicador(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        nova = (await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)).json()
        resposta = await c.patch(
            f"/organizacoes/{org}/conexoes/{nova['id']}", json={"etapa": "pronta"}
        )
        assert resposta.status_code == 409
