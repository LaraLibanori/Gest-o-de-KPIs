from tests.conftest import criar_usuario

CONEXAO = {
    "nome": "Local",
    "host": "localhost",
    "porta": 55432,
    "banco": "postgres",
    "usuario": "postgres",
    "senha": "postgres",
}


async def _preparar(c, admin):
    org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
    base = f"/organizacoes/{org}/conexoes"
    conexao = (await c.post(base, json=CONEXAO)).json()["id"]
    indicador = await admin.fetchval(
        "insert into indicadores (conexao_id, nome, agregacao, origem, ordem)"
        " values ($1::uuid, 'Vendas', 'contagem', 'manual', 0) returning id",
        conexao,
    )
    return org, f"{base}/{conexao}/indicadores/{indicador}"


async def test_dono_define_e_apaga_a_meta(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")

    async with cliente(ana) as c:
        _, url = await _preparar(c, admin)
        assert (await c.patch(url, json={"meta": 1500})).json()["meta"] == 1500
        assert (await c.patch(url, json={"meta": None})).json()["meta"] is None
        assert (await c.patch(url, json={"meta": -1})).status_code == 422


async def test_membro_nao_mexe_na_meta(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bob = await criar_usuario(admin, "bob@exemplo.com")

    async with cliente(ana) as c:
        org, url = await _preparar(c, admin)
        await c.post(f"/organizacoes/{org}/convites", json={"email": "bob@exemplo.com"})

    async with cliente(bob) as c:
        assert (await c.patch(url, json={"meta": 10})).status_code == 403
