import asyncio
import json
import logging
import os
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

registro = logging.getLogger("kpi")

# O terceiro campo diz se o provedor cobra: no OpenRouter so entra preco zero.
PROVEDORES = [
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
        colunas: list[Coluna]

    return Sugestoes


_modelos: list[str] | None = None
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


# A lista muda sem aviso, entao e descoberta na hora e guardada.
async def modelos() -> list[str]:
    global _modelos
    async with _tranca:
        if _modelos is not None:
            return _modelos
        encontrados: list[tuple[int, float, str]] = []
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
                for m in lista:
                    if not _serve(m, so_gratuito):
                        continue
                    nome = f"{provedor}/{m['id']}"
                    porte = -1.0 if nome == SORTEIO else _porte(m["id"])
                    encontrados.append((ordem, -porte, nome))
        _modelos = [nome for _, _, nome in sorted(encontrados)]
        return _modelos


# O Router guarda quem falhou e deixa de molho pelo tempo do descanso.
async def _montar(disponiveis: list[str]):
    global _roteador
    if _roteador is None:
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


async def _perguntar(mensagens: list[dict], colunas: list[str]) -> list | None:
    disponiveis = await modelos()
    if not disponiveis:
        return None

    import litellm

    # Cada tentativa que falha despeja o traceback inteiro no log.
    litellm.suppress_debug_info = True
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

    esquema = _esquema(colunas)
    roteador = await _montar(disponiveis)
    esperadas = set(colunas)
    melhor: list = []

    for modelo in disponiveis[:TENTATIVAS]:
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
        except Exception:  # noqa: BLE001 - sugestao nunca pode derrubar o catalogo
            registro.warning("%s não respondeu", modelo)
            continue

        vistas = {c.coluna for c in dados.colunas}
        if vistas == esperadas:
            return dados.colunas
        registro.warning("%s deixou de fora %d coluna", modelo, len(esperadas - vistas))
        if len(vistas) > len(melhor):
            melhor = dados.colunas

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
        colunas,
    )
    if not sugeridas:
        return {}
    conhecidas = set(colunas)
    return {s.coluna: s for s in sugeridas if s.coluna in conhecidas}
