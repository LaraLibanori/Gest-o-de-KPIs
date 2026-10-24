import json
from types import SimpleNamespace

from app import llm


class RoteadorFalso:
    def __init__(self, quebrados):
        self.quebrados = quebrados
        self.chamados = []

    async def acompletion(self, model, **kwargs):
        self.chamados.append(model)
        if model in self.quebrados:
            raise TimeoutError("demorou")
        conteudo = json.dumps(
            {"itens": [{"id": 1, "movimento": "subiu", "motivos": "", "sugestao": ""}]}
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=conteudo))]
        )


async def _preparar(monkeypatch, roteador):
    async def modelos():
        return ["p/lento", "q/rapido"]

    async def montar(_):
        return roteador

    monkeypatch.setattr(llm, "modelos", modelos)
    monkeypatch.setattr(llm, "_montar", montar)
    monkeypatch.setattr(llm, "_demora", {})
    monkeypatch.setattr(llm, "_de_molho", {})


async def _perguntar():
    return await llm._perguntar([], llm.Explicacoes, {1}, "id")


async def test_modelo_que_falhou_fica_de_molho_e_o_rapido_vai_na_frente(monkeypatch):
    roteador = RoteadorFalso(quebrados={"p/lento"})
    await _preparar(monkeypatch, roteador)

    assert await _perguntar()
    assert roteador.chamados == ["p/lento", "q/rapido"]

    roteador.chamados.clear()
    assert await _perguntar()
    assert roteador.chamados == ["q/rapido"]


async def test_com_todos_de_molho_ainda_tenta_a_lista_inteira(monkeypatch):
    roteador = RoteadorFalso(quebrados={"p/lento", "q/rapido"})
    await _preparar(monkeypatch, roteador)

    assert await _perguntar() is None
    roteador.chamados.clear()
    assert await _perguntar() is None
    assert roteador.chamados == ["p/lento", "q/rapido"]
