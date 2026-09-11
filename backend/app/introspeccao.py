import asyncpg

# Quanto valor distinto uma coluna pode ter e ainda servir de dimensao.
LIMITE_DIMENSAO = 100
AMOSTRA = 5000

# Continuo e sempre metrica: dinheiro tem valor quase unico por natureza.
CONTINUOS = ("numeric", "decimal", "real", "double", "money")
INTEIROS = ("smallint", "integer", "bigint")
TEMPO = ("date", "timestamp", "time")

# Acima disso a coluna e identificador; abaixo daquilo, serve de dimensao.
PROPORCAO_IDENTIFICADOR = 0.95
PROPORCAO_DIMENSAO = 0.5

TIPOS = {"r": "tabela", "p": "tabela", "v": "view", "m": "view materializada"}

# pg_class porque o information_schema nao enxerga view materializada.
# So entra o que o usuario da conexao pode mesmo ler.
RELACOES = """
    select n.nspname as esquema, c.relname as nome, c.relkind::text as especie
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relkind in ('r', 'p', 'v', 'm')
      and n.nspname not in ('pg_catalog', 'information_schema')
      and n.nspname not like 'pg_toast%'
      and has_table_privilege(c.oid, 'select')
      and not exists (
        select 1 from pg_depend d
        where d.objid = c.oid and d.deptype = 'e'
      )
    order by n.nspname, c.relname
"""

COLUNAS = """
    select a.attname as coluna, format_type(a.atttypid, a.atttypmod) as tipo
    from pg_attribute a
    join pg_class c on c.oid = a.attrelid
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = $1 and c.relname = $2
      and a.attnum > 0 and not a.attisdropped
    order by a.attnum
"""

# Tabela e view materializada tem estatistica pronta; view comum nao tem.
ESTATISTICA = """
    select s.attname, s.n_distinct, c.reltuples
    from pg_stats s
    join pg_namespace n on n.nspname = s.schemaname
    join pg_class c on c.relname = s.tablename and c.relnamespace = n.oid
    where s.schemaname = $1 and s.tablename = $2
"""


def citar(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def qualificar(esquema: str, nome: str) -> str:
    return f"{citar(esquema)}.{citar(nome)}"


def partir(referencia: str) -> tuple[str, str]:
    esquema, _, nome = referencia.partition(".")
    return (esquema, nome) if nome else ("public", esquema)


async def listar_relacoes(conexao: asyncpg.Connection) -> list[dict]:
    linhas = await conexao.fetch(RELACOES)
    return [
        {
            "nome": r["nome"]
            if r["esquema"] == "public"
            else f"{r['esquema']}.{r['nome']}",
            "tipo": TIPOS[r["especie"]],
        }
        for r in linhas
    ]


async def _cardinalidades(
    conexao: asyncpg.Connection, esquema: str, nome: str, colunas: list[str]
) -> tuple[dict[str, int], float | None]:
    estatisticas = await conexao.fetch(ESTATISTICA, esquema, nome)
    if estatisticas:
        linhas = float(estatisticas[0]["reltuples"] or 0)
        valores = {}
        for e in estatisticas:
            distintos = float(e["n_distinct"] or 0)
            if distintos > 0:
                valores[e["attname"]] = int(distintos)
            elif distintos < 0 and linhas > 0:
                valores[e["attname"]] = max(1, round(-distintos * linhas))
        return valores, linhas or None

    # View comum nao tem estatistica: conta sobre uma amostra.
    if not colunas:
        return {}, None
    contagens = ", ".join(f"count(distinct {citar(c)}) as {citar(c)}" for c in colunas)
    alvo = qualificar(esquema, nome)
    linha = await conexao.fetchrow(
        f"select count(*) as total, {contagens}"
        f" from (select * from {alvo} limit {AMOSTRA}) amostra"
    )
    total = linha["total"]
    return {c: linha[c] for c in colunas}, float(total) if total else None


def identificador(coluna: str) -> bool:
    return coluna == "id" or coluna.endswith("_id")


def classificar(
    coluna: str, tipo: str, cardinalidade: int | None, linhas: float | None
) -> str:
    if tipo.startswith(TEMPO):
        return "tempo"
    if identificador(coluna):
        return "ignorar"
    if tipo.startswith(CONTINUOS):
        return "metrica"

    proporcao = cardinalidade / linhas if cardinalidade and linhas else None
    if proporcao is not None and proporcao >= PROPORCAO_IDENTIFICADOR:
        return "ignorar"
    if tipo.startswith(INTEIROS):
        return "metrica"
    if tipo.startswith("boolean"):
        return "dimensao"
    if proporcao is not None:
        return "dimensao" if proporcao <= PROPORCAO_DIMENSAO else "ignorar"
    if cardinalidade is not None and cardinalidade <= LIMITE_DIMENSAO:
        return "dimensao"
    return "ignorar"


async def ler_catalogo(conexao: asyncpg.Connection, referencia: str) -> list[dict]:
    esquema, nome = partir(referencia)
    colunas = await conexao.fetch(COLUNAS, esquema, nome)
    if not colunas:
        raise ValueError(f"a tabela {referencia} não foi encontrada")

    nomes = [c["coluna"] for c in colunas]
    cardinalidades, linhas = await _cardinalidades(conexao, esquema, nome, nomes)

    return [
        {
            "coluna": c["coluna"],
            "tipo": c["tipo"],
            "cardinalidade": cardinalidades.get(c["coluna"]),
            "papel": classificar(
                c["coluna"], c["tipo"], cardinalidades.get(c["coluna"]), linhas
            ),
            "ordem": i,
        }
        for i, c in enumerate(colunas)
    ]
