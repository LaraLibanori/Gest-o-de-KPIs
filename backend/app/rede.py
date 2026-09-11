import asyncio
import ipaddress
import socket

from .config import PERMITIR_REDE_INTERNA


class RedeInterna(Exception):
    pass


# O banco do cliente e um host que ele digita. Sem isso, dava para apontar a
# conexao para um endereco interno e usar a API como sonda.
async def conferir(host: str) -> None:
    if PERMITIR_REDE_INTERNA:
        return
    try:
        enderecos = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except OSError as e:
        raise RedeInterna("não foi possível resolver o host") from e

    for info in enderecos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise RedeInterna("endereço de rede interna não é aceito")
