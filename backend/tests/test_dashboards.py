from uuid import uuid4

from tests.conftest import criar_usuario


async def test_dashboard_nao_vaza_para_outra_organizacao(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bob = await criar_usuario(admin, "bob@exemplo.com")

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        criado = await c.post(
            f"/organizacoes/{org}/dashboards", json={"nome": "Vendas"}
        )
        assert criado.status_code == 201
        dashboard = criado.json()["id"]
        lista = (await c.get(f"/organizacoes/{org}/dashboards")).json()
        assert [d["nome"] for d in lista] == ["Vendas"]

    async with cliente(bob) as c:
        assert (await c.get(f"/organizacoes/{org}/dashboards")).status_code == 404
        resposta = await c.get(f"/organizacoes/{org}/dashboards/{dashboard}")
        assert resposta.status_code == 404


async def test_dashboard_recusa_indicador_que_nao_e_da_organizacao(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        dashboard = (
            await c.post(f"/organizacoes/{org}/dashboards", json={"nome": "Vendas"})
        ).json()["id"]
        resposta = await c.put(
            f"/organizacoes/{org}/dashboards/{dashboard}/indicadores",
            json={"indicadores": [str(uuid4())]},
        )
        assert resposta.status_code == 422
