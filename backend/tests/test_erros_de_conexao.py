import socket

import asyncpg
import pytest

from app.routers.comum import _postgres, _rede

# O driver devolve a mensagem em ingles e com codigo; quem le e o dono da empresa.
# O que importa e que nenhum texto cru chegue na tela.


def erro(sqlstate: str, mensagem: str) -> asyncpg.PostgresError:
    e = asyncpg.PostgresError(mensagem)
    e.sqlstate = sqlstate
    return e


@pytest.mark.parametrize(
    ("sqlstate", "esperado"),
    [
        ("28P01", "senha incorreta"),
        ("3D000", "banco informado não existe"),
        ("28000", "não tem permissão de entrada"),
        ("42501", "não tem permissão para ler"),
        ("53300", "número de conexões no limite"),
        ("3F000", "schema informado não existe"),
        ("42P01", "tabela informada não existe"),
    ],
)
def test_traduz_codigo_do_postgres(sqlstate, esperado):
    assert esperado in _postgres(erro(sqlstate, "detalhe interno do driver"))


def test_traduz_mesagem_quando_o_codigo_nao_ajuda():
    # Alguns servidores relatam falha de autenticacao com codigo generico.
    assert "senha incorreta" in _postgres(
        erro("XX000", 'password authentication failed for user "leitor"')
    )


def test_nao_deixa_passar_mensagem_crua():
    traduzido = _postgres(erro("XX000", "ERRO FATAL: Buffer overflow detected"))
    assert "buffer overflow" not in traduzido.lower()
    assert "não foi possível conectar" in traduzido.lower()


def test_traduz_falha_de_rede():
    assert "recusou" in _rede(ConnectionRefusedError(111, "Connection refused")).lower()
    assert "resolver o host" in _rede(socket.gaierror("Name or service not known"))
    assert "alcançar" in _rede(OSError("rede caiu")).lower()
