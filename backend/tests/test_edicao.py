from tests.conftest import criar_usuario

CONEXAO = {
    "nome": "Producao",
    "host": "db.exemplo.com",
    "porta": 5432,
    "banco": "vendas",
    "usuario": "leitor",
    "senha": "segredo-do-banco",
}

SEM_DNS = {**CONEXAO, "host": "nao-existe.invalid"}


async def test_provar_nao_cria_nada(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]

        resposta = await c.post(f"/organizacoes/{org}/conexoes/provar", json=SEM_DNS)
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["ok"] is False
        assert corpo["erro"]
        assert corpo["relacoes"] == []
        assert (await c.get(f"/organizacoes/{org}/conexoes")).json() == []


async def test_provar_aceita_esquema(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        resposta = await c.post(
            f"/organizacoes/{org}/conexoes/provar",
            json={**SEM_DNS, "esquema": "  loja  "},
        )
        assert resposta.status_code == 200


async def test_esquema_vazio_vira_todos(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        nova = (await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)).json()
        assert nova["esquema"] is None

        trocada = await c.patch(
            f"/organizacoes/{org}/conexoes/{nova['id']}", json={"esquema": "  "}
        )
        assert trocada.json()["esquema"] is None


async def test_editar_troca_o_schema(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        nova = (await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)).json()

        trocada = await c.patch(
            f"/organizacoes/{org}/conexoes/{nova['id']}",
            json={"esquema": "moda_loja_schema", "banco": "postgres", "porta": 6543},
        )
        assert trocada.status_code == 200
        corpo = trocada.json()
        assert corpo["esquema"] == "moda_loja_schema"
        assert corpo["banco"] == "postgres"
        assert corpo["porta"] == 6543


async def test_editar_renomeia_e_bloqueia_repetido(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        a = (await c.post(f"/organizacoes/{org}/conexoes", json=CONEXAO)).json()
        b = (
            await c.post(
                f"/organizacoes/{org}/conexoes", json={**CONEXAO, "nome": "Homolog"}
            )
        ).json()

        ok = await c.patch(
            f"/organizacoes/{org}/conexoes/{a['id']}", json={"nome": "Loja"}
        )
        assert ok.json()["nome"] == "Loja"

        choca = await c.patch(
            f"/organizacoes/{org}/conexoes/{b['id']}", json={"nome": "loja"}
        )
        assert choca.status_code == 409
        igual = await c.patch(
            f"/organizacoes/{org}/conexoes/{b['id']}", json={"nome": "Homolog"}
        )
        assert igual.status_code == 200


async def test_mexer_no_acesso_zera_verificacao_mas_renomear_nao(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        base = f"/organizacoes/{org}/conexoes"
        nova = (await c.post(base, json=CONEXAO)).json()
        await c.post(f"{base}/{nova['id']}/verificar")
        verificada = (await c.get(base)).json()[0]["verificada_em"]
        assert verificada is not None

        trocada = await c.patch(f"{base}/{nova['id']}", json={"esquema": "loja"})
        assert trocada.json()["verificada_em"] is None

        await c.post(f"{base}/{nova['id']}/verificar")
        assert (await c.get(base)).json()[0]["verificada_em"] is not None
        renomeada = await c.patch(f"{base}/{nova['id']}", json={"nome": "Outra"})
        assert renomeada.json()["verificada_em"] is not None


async def test_campo_obrigatorio_vazio_da_422_e_nao_500(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        base = f"/organizacoes/{org}/conexoes"
        nova = (await c.post(base, json=CONEXAO)).json()

        for corpo in ({"nome": "   "}, {"host": ""}, {"banco": "  "}, {"porta": None}):
            resposta = await c.patch(f"{base}/{nova['id']}", json=corpo)
            assert resposta.status_code == 422, corpo
        intacta = (await c.get(base)).json()[0]
        assert intacta["nome"] == "Producao"
        assert intacta["banco"] == "vendas"


async def test_membro_nao_testa_conexao(cliente, admin):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bob = await criar_usuario(admin, "bob@exemplo.com")
    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        await c.post(f"/organizacoes/{org}/convites", json={"email": "bob@exemplo.com"})

    async with cliente(bob) as c:
        resposta = await c.post(f"/organizacoes/{org}/conexoes/provar", json=SEM_DNS)
        assert resposta.status_code == 403


async def test_verificar_filtra_por_esquema(cliente, admin, monkeypatch):
    ana = await criar_usuario(admin, "ana@exemplo.com")

    vistas: list[str | None] = []

    async def fake_consultar(conexao, tarefa):
        from tests.test_introspeccao import conexao_falsa

        vistas.append(conexao.esquema)
        return await tarefa(conexao_falsa())

    monkeypatch.setattr("app.routers.conexoes.consultar", fake_consultar)
    monkeypatch.setattr(
        "app.routers.conexoes.listar_relacoes",
        lambda c, esquema: _relacoes(esquema),
    )
    monkeypatch.setattr("app.routers.conexoes.listar_esquemas", lambda c: _esquemas())

    async with cliente(ana) as c:
        org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
        nova = (
            await c.post(
                f"/organizacoes/{org}/conexoes", json={**CONEXAO, "esquema": "loja"}
            )
        ).json()

        await c.post(f"/organizacoes/{org}/conexoes/{nova['id']}/verificar")
        assert vistas[-1] == "loja"

        await c.post(
            f"/organizacoes/{org}/conexoes/{nova['id']}/verificar",
            params={"esquema": "outro"},
        )
        assert vistas[-1] == "loja"
        gravada = (await c.get(f"/organizacoes/{org}/conexoes")).json()[0]
        assert gravada["esquema"] == "loja"


async def _relacoes(esquema):
    if esquema == "loja":
        return [{"nome": "loja.vendas", "tipo": "tabela"}]
    return [
        {"nome": "vendas", "tipo": "tabela"},
        {"nome": "loja.vendas", "tipo": "tabela"},
    ]


async def _esquemas():
    return ["loja", "public"]
