import hashlib
import re
import unicodedata


def normalizar(texto: str) -> str:
    limpo = unicodedata.normalize("NFKD", texto.lower())
    limpo = "".join(c for c in limpo if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]|_", " ", limpo).split())


def chave(texto: str) -> str:
    return hashlib.md5(normalizar(texto).encode(), usedforsecurity=False).hexdigest()


def palavras(texto: str) -> set[str]:
    return {p for p in normalizar(texto).split() if len(p) > 2}


def _br(valor: float, casas: int) -> str:
    texto = f"{valor:,.{casas}f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return texto[:-2] if casas == 1 and texto.endswith(",0") else texto


def quantia(valor: float | None, dinheiro: bool) -> str:
    if valor is None:
        return "sem dado"
    sinal = "-" if valor < 0 else ""
    v = abs(valor)
    if v >= 1e6:
        corpo = f"{_br(v / 1e6, 1)} mi"
    elif v >= 1e4:
        corpo = f"{_br(v / 1e3, 1)} mil"
    else:
        corpo = _br(v, 2 if dinheiro and v < 100 else 0)
    return f"{sinal}R$ {corpo}" if dinheiro else f"{sinal}{corpo}"


def percentual(valor: float | None, com_sinal: bool = True) -> str:
    if valor is None:
        return "sem comparação"
    if not com_sinal:
        valor = abs(valor)
    sinal = "+" if valor > 0 and com_sinal else ""
    return f"{sinal}{_br(valor, 1)}%"
