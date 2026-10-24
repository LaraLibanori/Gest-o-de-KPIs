import asyncio
import ipaddress
import socket

from .config import PERMITIR_REDE_INTERNA


class RedeInterna(Exception):
    pass


async def conferir(host: str) -> str:
    if PERMITIR_REDE_INTERNA:
        return host
    try:
        enderecos = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except OSError as e:
        raise RedeInterna(
            "Não encontramos esse endereço de servidor. Confira se está escrito certo."
        ) from e

    for info in enderecos:
        ip = ipaddress.ip_address(info[4][0])
        embutido = getattr(ip, "ipv4_mapped", None) or getattr(ip, "sixtofour", None)
        if not ip.is_global or (embutido and not embutido.is_global):
            raise RedeInterna(
                "Endereços de rede interna, como localhost, não são aceitos."
            )

    quatro = [i for i in enderecos if i[0] == socket.AF_INET]
    return (quatro or enderecos)[0][4][0]
