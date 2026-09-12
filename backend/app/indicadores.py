from .texto import normalizar, palavras

QUANTOS = 5

PAPEIS_ACEITOS = {
    "soma": ("metrica",),
    "media": ("metrica",),
    "minimo": ("metrica",),
    "maximo": ("metrica",),
    "distintos": ("dimensao", "ignorar"),
    "contagem": (),
}

# Somar preco unitario ou taxa entre linhas nao significa nada: so media serve.
NAO_SOMAVEIS = ("unitario", "unitaria", "medio", "media", "taxa", "percentual")

INTEIROS = ("int", "bigint", "smallint")


def _rotulo(campo) -> str:
    return campo.rotulo or campo.coluna


def _texto(campo) -> str:
    return normalizar(f"{campo.coluna} {_rotulo(campo)}")


# Chave que nomeia alguma coisa serve para contar; a chave da propria linha nao.
def _entidade(campo) -> bool:
    return campo.coluna != "id" and campo.coluna.endswith("_id")


def _somavel(campo) -> bool:
    return not any(p in _texto(campo) for p in NAO_SOMAVEIS)


# Quem se chama total costuma ser o valor cheio da linha, e dinheiro vem antes
# de contagem.
def _peso(campo) -> tuple:
    return (
        0 if "total" in _texto(campo) else 1,
        1 if campo.tipo.startswith(INTEIROS) else 0,
        campo.ordem,
    )


def _parecido(pista: str | None, campo) -> int:
    if not pista:
        return 0
    return len(palavras(pista) & palavras(f"{campo.coluna} {_rotulo(campo)}"))


def _separar(campos):
    return (
        [c for c in campos if c.papel == "metrica"],
        [c for c in campos if c.papel == "dimensao"],
        [c for c in campos if c.papel == "tempo"],
        [c for c in campos if c.papel == "ignorar" and _entidade(c)],
    )


# Sem segmento, ou com segmento que nao cobre: indicador direto do catalogo.
def por_regra(campos, quantos: int = QUANTOS) -> list[dict]:
    metricas, dimensoes, tempos, chaves = _separar(campos)
    somaveis = sorted([m for m in metricas if _somavel(m)], key=_peso)
    tempo = tempos[0].coluna if tempos else None

    propostas: list[tuple[str, str, object]] = []
    if campos:
        propostas.append(("Total de registros", "contagem", None))
    if somaveis:
        propostas.append((f"Soma de {_rotulo(somaveis[0])}", "soma", somaveis[0]))
    if metricas:
        propostas.append((f"Média de {_rotulo(metricas[0])}", "media", metricas[0]))
    for c in chaves + dimensoes:
        propostas.append((f"Quantidade de {_rotulo(c)}", "distintos", c))
    for m in somaveis[1:]:
        propostas.append((f"Soma de {_rotulo(m)}", "soma", m))

    indicadores: list[dict] = []
    vistos: set[str] = set()
    for nome, agregacao, campo in propostas:
        if len(indicadores) == quantos or nome in vistos:
            continue
        vistos.add(nome)
        indicadores.append(
            {
                "nome": nome,
                "agregacao": agregacao,
                "coluna": campo.coluna if campo else None,
                "dimensao": None,
                "tempo": tempo,
                "periodo": "sempre",
                "origem": "regra",
                "ordem": len(indicadores) + 1,
            }
        )
    return indicadores


# Liga um indicador do segmento a uma coluna do catalogo. Match fraco ou
# empatado vira escolha do usuario, nao chute.
def casar(kpi, campos) -> dict:
    aceitos = PAPEIS_ACEITOS[kpi.agregacao]
    if not aceitos:
        return {"situacao": "pronto", "coluna": None, "candidatos": []}

    candidatos = [c for c in campos if c.papel in aceitos]
    if not candidatos:
        return {"situacao": "impossivel", "coluna": None, "candidatos": []}

    ordenados = sorted(candidatos, key=lambda c: (-_parecido(kpi.pista, c), c.ordem))
    nomes = [c.coluna for c in ordenados]
    melhor = _parecido(kpi.pista, ordenados[0])
    empate = len(ordenados) > 1 and _parecido(kpi.pista, ordenados[1]) == melhor
    exigido = (len(palavras(kpi.pista or "")) + 1) // 2

    if melhor == 0 or empate or melhor < exigido:
        return {"situacao": "escolher", "coluna": None, "candidatos": nomes}
    return {"situacao": "pronto", "coluna": ordenados[0].coluna, "candidatos": nomes}
