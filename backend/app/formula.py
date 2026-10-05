import re

from .introspeccao import citar

# O texto digitado nunca e repassado: o SQL e remontado token por token.
NUMERO = re.compile(r"\d+(?:\.\d+)?")
COLUNA = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

FUNCOES = {
    "abs": (1, 1),
    "ceil": (1, 1),
    "floor": (1, 1),
    "sqrt": (1, 1),
    "round": (1, 2),
    "power": (2, 2),
    "coalesce": (1, None),
    "least": (1, None),
    "greatest": (1, None),
}

PALAVRAS = {
    "select": "fórmula não busca em outra tabela",
    "from": "fórmula não busca em outra tabela",
    "where": "fórmula não filtra",
    "having": "fórmula não filtra",
    "join": "fórmula não junta tabelas",
    "union": "fórmula não junta consultas",
    "insert": "fórmula não escreve",
    "update": "fórmula não escreve",
    "delete": "fórmula não apaga",
    "drop": "fórmula não mexe no esquema",
    "truncate": "fórmula não mexe no esquema",
    "grant": "fórmula não mexe em permissão",
    "into": "fórmula não escreve",
    "case": "fórmula não tem condição",
    "when": "fórmula não tem condição",
}


class FormulaInvalida(ValueError):
    pass


class _Leitor:
    def __init__(self, texto: str, conhecidos: set[str], permitidos: set[str]):
        self.texto = texto
        self.pos = 0
        self.conhecidos = conhecidos
        self.permitidos = permitidos
        self.ordem = sorted(conhecidos | permitidos, key=len, reverse=True)
        self.usadas: set[str] = set()

    def sobra(self) -> str:
        return self.texto[self.pos :].lstrip()

    def pular(self) -> None:
        while self.pos < len(self.texto) and self.texto[self.pos].isspace():
            self.pos += 1

    def comecar(self, marca: str) -> bool:
        self.pular()
        if self.texto.startswith(marca, self.pos):
            self.pos += len(marca)
            return True
        return False

    def fim(self) -> bool:
        self.pular()
        return self.pos >= len(self.texto)

    def expressao(self) -> str:
        texto = self.produto()
        while True:
            self.pular()
            if self.comecar("+"):
                texto = f"({texto} + {self.produto()})"
            elif self.comecar("-"):
                texto = f"({texto} - {self.produto()})"
            else:
                return texto

    def produto(self) -> str:
        texto = self.fator()
        while True:
            self.pular()
            if self.comecar("*"):
                texto = f"({texto} * {self.fator()})"
            elif self.comecar("/"):
                texto = f"({texto} / nullif(({self.fator()})::numeric, 0))"
            else:
                return texto

    def fator(self) -> str:
        self.pular()
        if self.comecar("+"):
            return self.fator()
        if self.comecar("-"):
            return f"-({self.fator()})"
        return self.primario()

    def coluna_ou_nada(self) -> str | None:
        """Casa o nome real do catalogo, que pode ter espaco no meio."""
        self.pular()
        achado = COLUNA.match(self.texto, self.pos)
        if achado and achado.group(0).lower() in FUNCOES:
            depois = self.texto[achado.end() :].lstrip()
            if depois.startswith("("):
                return None
        for nome in self.ordem:
            if self.texto.startswith(nome, self.pos):
                vizinho = self.texto[self.pos + len(nome) : self.pos + len(nome) + 1]
                if vizinho and (vizinho.isalnum() or vizinho == "_"):
                    continue
                self.pos += len(nome)
                return nome
        return None

    def primario(self) -> str:
        self.pular()
        if self.pos >= len(self.texto):
            raise FormulaInvalida("fórmula está incompleta")

        if self.comecar("("):
            dentro = self.expressao()
            if not self.comecar(")"):
                raise FormulaInvalida("fórmula tem parêntese que não fecha")
            return f"({dentro})"

        achado = NUMERO.match(self.texto, self.pos)
        if achado:
            self.pos = achado.end()
            return achado.group(0)

        achado = COLUNA.match(self.texto, self.pos)
        if not achado:
            raise FormulaInvalida("fórmula tem caractere que não entra em conta")
        nome = achado.group(0)

        depois = self.texto[achado.end() :].lstrip()
        if depois.startswith("("):
            baixo = nome.lower()
            if baixo not in FUNCOES:
                raise FormulaInvalida(f"a função {nome} não existe")
            self.pos = achado.end()
            self.comecar("(")
            minimo, maximo = FUNCOES[baixo]
            argumentos = [self.expressao()]
            while self.comecar(","):
                argumentos.append(self.expressao())
            if not self.comecar(")"):
                raise FormulaInvalida("fórmula tem parêntese que não fecha")
            if len(argumentos) < minimo or (maximo and len(argumentos) > maximo):
                raise FormulaInvalida(f"{nome} não aceita {len(argumentos)} argumentos")
            if baixo == "round" and len(argumentos) == 2:
                argumentos[0] = f"({argumentos[0]})::numeric"
            return f"{baixo}({', '.join(argumentos)})"

        if nome.lower() in PALAVRAS:
            raise FormulaInvalida(PALAVRAS[nome.lower()])

        coluna = self.coluna_ou_nada()
        if coluna is not None:
            if coluna in self.permitidos:
                self.usadas.add(coluna)
                return citar(coluna)
            raise FormulaInvalida(f"a coluna {coluna} não entra em conta")
        raise FormulaInvalida(f"a coluna {nome} não existe na tabela")


def analisar(
    formula: str, conhecidos: set[str], permitidos: set[str]
) -> tuple[str, set[str]]:
    """Confere a fórmula e devolve o SQL pronto e as colunas que ela usa."""
    if not formula or not formula.strip():
        raise FormulaInvalida("fórmula vazia")
    if len(formula) > 400:
        raise FormulaInvalida("fórmula longa demais")

    leitor = _Leitor(formula, conhecidos, permitidos)
    sql = leitor.expressao()
    if not leitor.fim():
        if leitor.sobra()[0] in "<>=!":
            raise FormulaInvalida("fórmula não compara valores")
        raise FormulaInvalida("fórmula tem sobra no fim")
    if not leitor.usadas:
        raise FormulaInvalida("fórmula precisa de pelo menos uma coluna")
    return sql, leitor.usadas


def derivar(campos) -> tuple[list[tuple[str, str]], list[str]]:
    """Monta o SQL dos campos calculados e devolve os que quebraram."""
    base = {c.coluna for c in campos if not c.formula}
    conhecidos = {c.coluna for c in campos}
    prontos: set[str] = set()
    saida: list[tuple[str, str]] = []
    quebrados: list[str] = []

    for campo in sorted(campos, key=lambda c: c.ordem):
        if not campo.formula or campo.coluna in prontos:
            continue
        try:
            sql, _ = analisar(campo.formula, conhecidos, base | prontos)
        except FormulaInvalida:
            quebrados.append(campo.coluna)
            continue
        saida.append((campo.coluna, sql))
        prontos.add(campo.coluna)

    return saida, quebrados
