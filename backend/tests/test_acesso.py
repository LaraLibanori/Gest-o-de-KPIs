from tests.conftest import criar_usuario

CONEXAO = {
    "nome": "Producao",
    "host": "db.exemplo.com",
    "porta": 5432,
    "banco": "vendas",
    "usuario": "leitor",
    "senha": "segredo-do-banco",
}


async def test_cria_organizacao_e_vira_dono(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")

    async with cliente(ana) as c:
        resposta = await c.post("/organizacoes", json={"nome": "Acme"})
        assert resposta.status_code == 201
        assert resposta.json()["papel"] == "dono"


async def test_quem_nao_participa_nao_enxerga(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bob = await criar_usuario(admin, "bob@exemplo.com")

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)

    async with cliente(bob) as c:
        assert (await c.get("/organizacoes")).json() == []
        # 404 e nao 403: nao pode nem confirmar que a organizacao existe.
        assert (await c.get(f"/organizacoes/{org}/membros")).status_code == 404
        assert (await c.get(f"/organizacoes/{org}/conexoes")).status_code == 404


async def test_membro_nao_apaga_nem_convida(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bob = await criar_usuario(admin, "bob@exemplo.com")

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        await c.post(f"/organizacoes/{org}/convites", json={"email": "bob@exemplo.com"})

    async with cliente(bob) as c:
        assert (await c.delete(f"/organizacoes/{org}")).status_code == 403
        resposta = await c.post(
            f"/organizacoes/{org}/convites", json={"email": "outro@exemplo.com"}
        )
        assert resposta.status_code == 403


async def test_sem_token_responde_401(cliente):
    async with cliente(None) as c:
        assert (await c.get("/organizacoes")).status_code == 401
