# Tabela e coluna não podem ir como parâmetro na query. Só entram no SQL se
# estiverem nesta lista. É o que evita SQL injection.

AGREGACOES = {"count", "sum", "avg", "min", "max"}

FONTES: dict[str, set[str]] = {
    "vendas": {"quantidade", "valor"},
}


def validar(fonte: str, coluna: str | None, agregacao: str) -> None:
    if agregacao not in AGREGACOES:
        raise ValueError(f"agregação inválida: {agregacao}")
    if fonte not in FONTES:
        raise ValueError(f"fonte inválida: {fonte}")
    if agregacao == "count":
        return
    if coluna not in FONTES[fonte]:
        raise ValueError(f"coluna inválida para {fonte}: {coluna}")
