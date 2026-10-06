from httpx import ASGITransport, AsyncClient


async def _chamar(caminho, cabecalhos=None):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(caminho, headers=cabecalhos)


async def test_com_segredo_definido_a_api_publica_nao_existe(banco, monkeypatch):
    monkeypatch.setattr("app.main.SEGREDO_SERVIDOR", "abc")
    assert (await _chamar("/perfil")).status_code == 404
    assert (
        await _chamar("/perfil", {"x-segredo-servidor": "errado"})
    ).status_code == 404
    assert (await _chamar("/health")).status_code == 200


async def test_com_o_segredo_certo_a_chamada_chega_na_autenticacao(banco, monkeypatch):
    monkeypatch.setattr("app.main.SEGREDO_SERVIDOR", "abc")
    resposta = await _chamar("/perfil", {"x-segredo-servidor": "abc"})
    assert resposta.status_code in (401, 403)
