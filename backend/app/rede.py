import asyncio
import ipaddress
import socket

from .config import PERMITIR_REDE_INTERNA


class RedeInterna(Exception):
    pass


# Conectar no ip conferido, e nao no nome, fecha a janela para o dns mudar.
async def conferir(host: str) -> str:
    if PERMITIR_REDE_INTERNA:
        return host
    try:
        enderecos = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except OSError as e:
        raise RedeInterna("não foi possível resolver o host") from e

    for info in enderecos:
        ip = ipaddress.ip_address(info[4][0])
        embutido = getattr(ip, "ipv4_mapped", None) or getattr(ip, "sixtofour", None)
        if not ip.is_global or (embutido and not embutido.is_global):
            raise RedeInterna("endereço de rede interna não é aceito")

    # IPv4 na frente: as funções da Vercel não saem por IPv6.
    quatro = [i for i in enderecos if i[0] == socket.AF_INET]
    return (quatro or enderecos)[0][4][0]
