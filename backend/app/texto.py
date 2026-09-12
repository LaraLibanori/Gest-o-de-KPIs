import hashlib
import re
import unicodedata


def normalizar(texto: str) -> str:
    limpo = unicodedata.normalize("NFKD", texto.lower())
    limpo = "".join(c for c in limpo if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]|_", " ", limpo).split())


# Chave do cache de classificacao. Md5 aqui nao guarda segredo, so identifica.
def chave(texto: str) -> str:
    return hashlib.md5(normalizar(texto).encode(), usedforsecurity=False).hexdigest()


def palavras(texto: str) -> set[str]:
    return {p for p in normalizar(texto).split() if len(p) > 2}
