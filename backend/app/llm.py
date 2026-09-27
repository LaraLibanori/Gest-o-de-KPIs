import asyncio
import json
import logging
import os
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

registro = logging.getLogger("kpi")

# Ordem da fila: NVIDIA (gratis) primeiro, OpenRouter e Groq de reserva.
# O ultimo campo filtra so preco zero: vale pro OpenRouter, que tem os dois.
# A Groq lista o preco do plano pago, mas a conta free so leva rate limit.
PROVEDORES = [
    ("nvidia_nim", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", True),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", True),
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", False),
]

# Sorteia um gratuito a cada chamada, as vezes demora demais: fica por ultimo.
SORTEIO = "openrouter/openrouter/free"

PORTE_DESCONHECIDO = 32.0
JANELA_MINIMA = 8192
TEMPO_LIMITE = 20
DESCANSO = 300
TENTATIVAS = 3

# Testado ao vivo: nunca respondeu, so ate estourar o tempo.
TRAVA = {"deepseek-ai/deepseek-v4.1-flash"}

# Nao fazem chat: embedding, guard, audio, imagem...
NAO_CHAT = (
    "embed",
    "rerank",
    "reward",
    "guard",
    "safety",
    "whisper",
    "asr",
    "tts",
    "audio",
    "image",
    "video",
    "flux",
    "ocr",
    "vlm",
    "vision",
)

# O 404 da NVIDIA nao conta tentativa, mas tem teto para nao prender a fila.
TETO_404 = 10

# Cache de 10 minutos: provedor que caiu numa chamada volta na proxima.
TTL_MODELOS = 600

# Erro de conta inteira: insistir nos outros modelos do mesmo provedor nao ajuda.
CONTA_FORA = ("RateLimitError", "AuthenticationError", "PermissionDeniedError")

# Em ingles porque os modelos pequenos seguem melhor; a saida continua em portugues.
INSTRUCAO = """You classify the columns of a business database table so that a
non-technical user can build KPI dashboards from them.

For each column, return:
- `rotulo`: a short label in Brazilian Portuguese, 1 to 4 words. Capitalize only
  the first word and proper nouns, the way Portuguese does: write "Forma de
  pagamento", never "Forma De Pagamento". Do not repeat the column name or the
  data type.
- `papel`: the role the column plays.

Roles, returned as these exact values:
- `metrica`: a number worth summing or averaging - money, quantity, weight, cost
- `dimensao`: used to group or filter - category, region, channel, status, name
- `tempo`: a date or a timestamp
- `ignorar`: a key, with no meaning of its own

Rules:
- Use the business description to disambiguate. "valor" in a clinic is the price
  of a procedure; in a store it is the amount of the sale.
- A key that identifies a real entity - customer, order, patient - is `ignorar`,
  because it is never summed. Still give it a good label: it gets counted.
- Judge by the column name and its type, not by how many distinct values it has.
- Return exactly one entry per column received. Never invent or drop a column.

Example, for a bookstore:
  isbn         text     -> rotulo "ISBN",           papel "ignorar"
  preco_capa   numeric  -> rotulo "Preço de capa",  papel "metrica"
  editora      text     -> rotulo "Editora",        papel "dimensao"
"""


class ColunaSugerida(BaseModel):
    coluna: str = Field(description="exact column name, as received")
    rotulo: str = Field(max_length=120, description="short label, in Portuguese")
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"] = Field(
        description="metrica sums, dimensao groups, tempo is a date, ignorar is a key"
    )


# Lista fechada no schema: quem respeita structured output nao inventa coluna.
def _esquema(colunas: list[str]) -> type[BaseModel]:
    class Coluna(ColunaSugerida):
        coluna: Literal[tuple(colunas)] = Field(  # type: ignore[valid-type]
            description="exact column name, as received"
        )

    class Sugestoes(BaseModel):
        itens: list[Coluna]

    return Sugestoes


GRAFICO = Literal["numero", "barra", "linha", "pizza", "tabela"]

INSTRUCAO_GRAFICO = """You choose how each KPI is shown on a dashboard.

Forms:
- `numero`: one headline value. The default when there is nothing to break it by.
- `barra`: ranked horizontal bars, one per category. Best to compare magnitude.
- `linha`: a trend over time. Only when the KPI follows a date.
- `pizza`: share of one whole. Only for few categories that add up to the total,
  and never to compare values that are close to each other.
- `tabela`: a plain table. Best when there are many categories, or when the exact
  numbers matter more than the shape.

Rules:
- Every KPI lists the forms it can support in `formas`. Pick only from that list.
- `numero` is the default for a headline figure. Most KPIs carry a date column,
  and that alone is not a reason for `linha`: pick `linha` only when the KPI is
  about how something evolves, not about its current size.
- With a breakdown, prefer `barra`. Use `pizza` only when the categories are few
  and clearly parts of one whole; `tabela` when there are many of them.
- Return exactly one entry per KPI received, using the name you were given."""


def _esquema_grafico(nomes: list[str]) -> type[BaseModel]:
    class Escolha(BaseModel):
        indicador: Literal[tuple(nomes)] = Field(  # type: ignore[valid-type]
            description="exact KPI name, as received"
        )
        grafico: GRAFICO = Field(description="one of the forms listed for that KPI")

    class Escolhas(BaseModel):
        itens: list[Escolha]

    return Escolhas


_modelos: list[str] | None = None
_modelos_em = 0.0
_roteador = None
_tranca = asyncio.Lock()


def disponivel() -> bool:
    return any(os.environ.get(p[2]) for p in PROVEDORES)


def _porte(nome: str) -> float:
    achados = re.findall(r"(\d+(?:\.\d+)?)b", nome.lower())
    return max(float(x) for x in achados) if achados else PORTE_DESCONHECIDO


def _gratuito(m: dict) -> bool:
    preco = m.get("pricing") or {}
    return all(float(preco.get(c, 0) or 0) == 0 for c in ("prompt", "completion"))


# Campo ausente nao reprova: nem todo provedor descreve os modelos igual.
def _serve(m: dict, so_gratuito: bool) -> bool:
    nome = m.get("id", "")
    if nome in TRAVA or any(p in nome.lower() for p in NAO_CHAT):
        return False
    if m.get("active") is False:
        return False
    if so_gratuito and not _gratuito(m):
        return False
    arquitetura = m.get("architecture") or {}
    for campo in ("input_modalities", "output_modalities"):
        modos = m.get(campo) or arquitetura.get(campo)
        if modos and "text" not in modos:
            return False
    recursos = m.get("supported_features") or m.get("supported_parameters")
    if recursos and not {"json_mode", "structured_outputs"} & set(recursos):
        return False
    janela = m.get("context_length") or m.get("context_window")
    return not (janela and janela < JANELA_MINIMA)


async def _listar(cliente: httpx.AsyncClient, base: str, chave: str) -> list[dict]:
    resposta = await cliente.get(
        f"{base}/models", headers={"Authorization": f"Bearer {chave}"}
    )
    resposta.raise_for_status()
    return resposta.json().get("data", [])


# A pagina free da NVIDIA marca os modelos com "Free Endpoint". Responde 202
# quando desconfia de bot: ai desiste na hora e segue sem a lista.
async def _gratuitos_nvidia(cliente: httpx.AsyncClient) -> set[str]:
    try:
        resposta = await cliente.get(
            "https://build.nvidia.com/models",
            params={"filters": "nimType:nim_type_preview", "pageSize": "96"},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://build.nvidia.com/",
            },
            timeout=5,
        )
        if resposta.status_code != 200:
            return set()
        html = resposta.text
    except httpx.HTTPError:
        return set()
    cartoes = []
    for marca in re.finditer(r"<a\s[^>]*>", html):
        rotulo = re.search(r'data-nvtrack-nav-object-label="([^"]+)"', marca.group(0))
        href = re.search(r'href="/([^"]+)"', marca.group(0))
        if rotulo and href and "/" in href.group(1):
            cartoes.append((href.group(1), marca.start()))
    gratuitos = set()
    for i, (nome, pos) in enumerate(cartoes):
        # O selo vem antes do nome, dentro do mesmo cartao.
        inicio = cartoes[i - 1][1] if i else 0
        if "Free Endpoint" in html[inicio:pos]:
            gratuitos.add(nome)
    return gratuitos


async def modelos() -> list[str]:
    global _modelos, _modelos_em
    async with _tranca:
        if _modelos is not None and time.monotonic() - _modelos_em < TTL_MODELOS:
            return _modelos
        # O litellm so conhece NVIDIA_NIM_API_KEY: espelha a nossa.
        if os.environ.get("NVIDIA_API_KEY"):
            os.environ.setdefault("NVIDIA_NIM_API_KEY", os.environ["NVIDIA_API_KEY"])
        encontrados: list[tuple[int, int, float, str]] = []
        gratuitos: set[str] = set()
        async with httpx.AsyncClient(timeout=10) as cliente:
            for ordem, (provedor, base, variavel, so_gratuito) in enumerate(PROVEDORES):
                chave = os.environ.get(variavel)
                if not chave:
                    continue
                try:
                    lista = await _listar(cliente, base, chave)
                except httpx.HTTPError:
                    registro.warning("não foi possível listar modelos de %s", provedor)
                    continue
                if provedor == "nvidia_nim":
                    gratuitos = await _gratuitos_nvidia(cliente)
                for m in lista:
                    if not _serve(m, so_gratuito):
                        continue
                    nome = f"{provedor}/{m['id']}"
                    livre = 0 if m["id"] in gratuitos else 1
                    porte = -1.0 if nome == SORTEIO else _porte(m["id"])
                    encontrados.append((ordem, livre, -porte, nome))
        _modelos = [nome for _, _, _, nome in sorted(encontrados)]
        _modelos_em = time.monotonic()
        return _modelos


# O Router guarda quem falhou e deixa de molho pelo tempo do descanso.
# Lista nova recria o roteador: provedor que voltou entra de volta.
async def _montar(disponiveis: list[str]):
    global _roteador
    if _roteador is not None and {m["model_name"] for m in _roteador.model_list} == set(
        disponiveis
    ):
        return _roteador
    from litellm import Router

    _roteador = Router(
        model_list=[
            {"model_name": m, "litellm_params": {"model": m}} for m in disponiveis
        ],
        cooldown_time=DESCANSO,
        allowed_fails=1,
        num_retries=0,
    )
    return _roteador


# Um de cada provedor por rodada: a reserva aparece ja na primeira falha.
def _intercalar(nomes: list[str]) -> list[str]:
    grupos: dict[str, list[str]] = {}
    for nome in nomes:
        grupos.setdefault(nome.split("/", 1)[0], []).append(nome)
    fila = []
    for i in range(max((len(g) for g in grupos.values()), default=0)):
        for grupo in grupos.values():
            if i < len(grupo):
                fila.append(grupo[i])
    return fila


async def _perguntar(
    mensagens: list[dict], esquema, esperadas: set[str], chave: str
) -> list | None:
    disponiveis = await modelos()
    if not disponiveis:
        return None

    import litellm

    # Cada tentativa que falha despeja o traceback inteiro no log.
    litellm.suppress_debug_info = True
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

    roteador = await _montar(disponiveis)
    melhor: list = []

    fila = _intercalar(disponiveis)
    tentativas = 0
    sem_entidade = 0
    while fila and tentativas < TENTATIVAS:
        modelo = fila.pop(0)
        tentativas += 1
        try:
            resposta = await roteador.acompletion(
                model=modelo,
                messages=mensagens,
                timeout=TEMPO_LIMITE,
                response_format=esquema,
            )
            dados = esquema.model_validate_json(resposta.choices[0].message.content)
        except ValidationError:
            registro.warning("%s respondeu fora do formato", modelo)
            continue
        except Exception as e:  # noqa: BLE001 - sugestao nunca derruba o catalogo
            provedor = modelo.split("/", 1)[0]
            if type(e).__name__ in CONTA_FORA:
                fila = [m for m in fila if not m.startswith(f"{provedor}/")]
                tentativas -= 1
                registro.warning("%s fora: pulando o provedor", provedor)
            elif (
                getattr(e, "status_code", None) == 404
                or "Not found for account" in str(e)
            ) and sem_entidade < TETO_404:
                # Sem direito ao modelo: tenta o proximo do mesmo provedor.
                sem_entidade += 1
                tentativas -= 1
                proximo = next((m for m in fila if m.startswith(f"{provedor}/")), None)
                if proximo:
                    fila.remove(proximo)
                    fila.insert(0, proximo)
            else:
                registro.warning("%s não respondeu", modelo)
            continue

        vistas = {getattr(c, chave) for c in dados.itens}
        if vistas == esperadas:
            return dados.itens
        registro.warning("%s deixou de fora %d coluna", modelo, len(esperadas - vistas))
        if len(vistas) > len(melhor):
            melhor = dados.itens

    return melhor or None


# Manda so nome, tipo e cardinalidade: nenhuma linha da tabela sai do banco.
async def sugerir(
    campos: list[dict], tabela: str, negocio: str | None
) -> dict[str, ColunaSugerida]:
    if not disponivel() or not campos:
        return {}

    pergunta = {
        "tabela": tabela,
        "negocio": negocio or "não informado",
        "colunas": [
            {
                "coluna": c["coluna"],
                "tipo": c["tipo"],
                "valores_distintos": c["cardinalidade"],
            }
            for c in campos
        ],
    }
    colunas = [c["coluna"] for c in campos]
    sugeridas = await _perguntar(
        [
            {"role": "system", "content": INSTRUCAO},
            {"role": "user", "content": json.dumps(pergunta, ensure_ascii=False)},
        ],
        _esquema(colunas),
        set(colunas),
        "coluna",
    )
    if not sugeridas:
        return {}
    conhecidas = set(colunas)
    return {s.coluna: s for s in sugeridas if s.coluna in conhecidas}


# A forma volta presa a lista fechada; o que nao servir cai fora depois.
async def sugerir_graficos(indicadores: list[dict]) -> dict[str, str]:
    if not disponivel() or not indicadores:
        return {}

    nomes = [i["nome"] for i in indicadores]
    escolhas = await _perguntar(
        [
            {"role": "system", "content": INSTRUCAO_GRAFICO},
            {"role": "user", "content": json.dumps(indicadores, ensure_ascii=False)},
        ],
        _esquema_grafico(nomes),
        set(nomes),
        "indicador",
    )
    if not escolhas:
        return {}
    return {e.indicador: e.grafico for e in escolhas if e.indicador in set(nomes)}
