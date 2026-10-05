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


async def test_listagem_monta_cada_dashboard_com_seus_indicadores_em_ordem(
    cliente, admin
):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    conexao = {
        "nome": "Local",
        "host": "localhost",
        "porta": 55432,
        "banco": "postgres",
        "usuario": "postgres",
        "senha": "postgres",
    }

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        base = f"/organizacoes/{org}"
        conexao_id = (await c.post(f"{base}/conexoes", json=conexao)).json()["id"]
        ids = [
            await admin.fetchval(
                "insert into indicadores (conexao_id, nome, agregacao, origem, ordem)"
                " values ($1::uuid, $2, 'contagem', 'manual', 0) returning id",
                conexao_id,
                nome,
            )
            for nome in ("A", "B")
        ]
        primeiro = (await c.post(f"{base}/dashboards", json={"nome": "um"})).json()
        segundo = (await c.post(f"{base}/dashboards", json={"nome": "dois"})).json()
        await c.put(
            f"{base}/dashboards/{primeiro['id']}/indicadores",
            json={"indicadores": [str(ids[0])]},
        )
        await c.put(
            f"{base}/dashboards/{segundo['id']}/indicadores",
            json={"indicadores": [str(ids[1]), str(ids[0])]},
        )

        lista = {d["nome"]: d for d in (await c.get(f"{base}/dashboards")).json()}

    assert [i["nome"] for i in lista["um"]["indicadores"]] == ["A"]
    assert [i["nome"] for i in lista["dois"]["indicadores"]] == ["B", "A"]
