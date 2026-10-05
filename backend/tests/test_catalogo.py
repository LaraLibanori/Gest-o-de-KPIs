from tests.conftest import criar_usuario


async def test_refazer_o_catalogo_guarda_campo_calculado_e_confirmacao(
    cliente, admin, monkeypatch
):
    monkeypatch.setattr("app.rede.PERMITIR_REDE_INTERNA", True)
    await admin.execute(
        "create table public.vendas_t (id bigserial primary key, valor numeric,"
        " custo numeric, dia date)"
    )
    ana = await criar_usuario(admin, "ana@exemplo.com")
    base = {
        "nome": "Local",
        "host": "localhost",
        "porta": 55432,
        "banco": "postgres",
        "usuario": "postgres",
        "senha": "postgres",
    }

    try:
        async with cliente(ana) as c:
            org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
            url = f"/organizacoes/{org}/conexoes"
            conexao = (await c.post(url, json=base)).json()["id"]
            await c.patch(f"{url}/{conexao}", json={"tabela_fato": "public.vendas_t"})

            catalogo = (await c.post(f"{url}/{conexao}/catalogo")).json()
            valor = next(k for k in catalogo if k["coluna"] == "valor")
            await c.patch(
                f"{url}/{conexao}/catalogo/{valor['id']}",
                json={"papel": "dimensao", "confirmado": True},
            )
            criado = await c.post(
                f"{url}/{conexao}/campos",
                json={"nome": "margem", "rotulo": "Margem", "formula": "valor - custo"},
            )
            assert criado.status_code == 201

            refeito = (await c.post(f"{url}/{conexao}/catalogo")).json()
            por_coluna = {k["coluna"]: k for k in refeito}
            assert "margem" in por_coluna
            assert por_coluna["valor"]["papel"] == "dimensao"
            assert por_coluna["valor"]["confirmado"]
        regra = await admin.fetchval(
            "select papel_regra from catalogo_campos where coluna = 'valor'"
        )
        assert regra == "metrica"
    finally:
        await admin.execute("drop table public.vendas_t")
