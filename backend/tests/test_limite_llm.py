from tests.conftest import criar_usuario

CONEXAO = {
    "nome": "Local",
    "host": "localhost",
    "porta": 55432,
    "banco": "postgres",
    "usuario": "postgres",
    "senha": "postgres",
}


async def _sugerir_vazio(*args, **kwargs):
    return {}


async def _preparar(c, monkeypatch, por_usuario, total):
    monkeypatch.setattr("app.routers.catalogo.disponivel", lambda: True)
    monkeypatch.setattr("app.routers.catalogo.sugerir", _sugerir_vazio)
    monkeypatch.setattr("app.limite_llm.POR_USUARIO", por_usuario)
    monkeypatch.setattr("app.limite_llm.TOTAL", total)
    org = (await c.post("/organizacoes", json={"nome": "Acme"})).json()["id"]
    url = f"/organizacoes/{org}/conexoes"
    conexao = (await c.post(url, json=CONEXAO)).json()["id"]
    return f"{url}/{conexao}/catalogo/rotulos"


async def test_usuario_passa_do_limite_diario_e_recebe_429(cliente, admin, monkeypatch):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        rota = await _preparar(c, monkeypatch, por_usuario=2, total=100)
        assert (await c.post(rota)).status_code == 200
        assert (await c.post(rota)).status_code == 200
        recusada = await c.post(rota)
    assert recusada.status_code == 429
    assert "limite diário" in recusada.json()["detail"]
    assert await admin.fetchval("select count(*) from uso_llm") == 2


async def test_teto_global_vale_para_todos_os_usuarios(cliente, admin, monkeypatch):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    bia = await criar_usuario(admin, "bia@exemplo.com")
    async with cliente(ana) as c:
        rota = await _preparar(c, monkeypatch, por_usuario=5, total=1)
        assert (await c.post(rota)).status_code == 200
    org = await admin.fetchval("select id from organizacoes")
    await admin.execute(
        "insert into organizacao_membros (organizacao_id, usuario_id, papel)"
        " values ($1, $2, 'dono')",
        org,
        bia,
    )
    async with cliente(bia) as c:
        assert (await c.post(rota)).status_code == 429


async def test_sem_chave_de_llm_nao_gasta_reserva(cliente, admin, monkeypatch):
    ana = await criar_usuario(admin, "ana@exemplo.com")
    async with cliente(ana) as c:
        rota = await _preparar(c, monkeypatch, por_usuario=1, total=1)
        monkeypatch.setattr("app.routers.catalogo.disponivel", lambda: False)
        assert (await c.post(rota)).status_code == 200
    assert await admin.fetchval("select count(*) from uso_llm") == 0
