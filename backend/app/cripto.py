from cryptography.fernet import Fernet, InvalidToken

from .config import APP_SECRET_KEY


def _cofre() -> Fernet:
    if not APP_SECRET_KEY:
        raise RuntimeError("APP_SECRET_KEY não definida")
    return Fernet(APP_SECRET_KEY.encode())


def cifrar(texto: str) -> str:
    return _cofre().encrypt(texto.encode()).decode()


def decifrar(texto: str) -> str:
    try:
        return _cofre().decrypt(texto.encode()).decode()
    except InvalidToken as e:
        raise RuntimeError("senha da conexão não pôde ser decifrada") from e
