import asyncio
import json
import logging
import os
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

registro = logging.getLogger("kpi")

PROVEDORES = [
    ("cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY"),
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
]

# Audio, moderacao e embedding nao servem para isso.
FORA = ("whisper", "tts", "orpheus", "guard", "embed", "compound")

TEMPO_LIMITE = 20

INSTRUCAO = """Você recebe as colunas de uma tabela de banco de dados e o ramo
da empresa. Devolve, para cada coluna, um rótulo curto em português e o papel
dela num painel de indicadores.

Papéis possíveis:
- metrica: número que faz sentido somar ou tirar média
- dimensao: serve para agrupar ou filtrar
- tempo: data ou instante
- ignorar: identificador, chave ou campo sem uso analítico

Use exatamente os nomes de coluna que receber, sem inventar nenhum."""


class ColunaSugerida(BaseModel):
    coluna: str
    rotulo: str = Field(max_length=120)
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"]


class Sugestoes(BaseModel):
    colunas: list[ColunaSugerida]


_modelos: list[str] | None = None
_tranca = asyncio.Lock()


def disponivel() -> bool:
    return any(os.environ.get(chave) for _, _, chave in PROVEDORES)


def _porte(nome: str) -> float:
    achados = re.findall(r"(\d+(?:\.\d+)?)b", nome.lower())
    return max(float(x) for x in achados) if achados else 0.0


async def _listar(cliente: httpx.AsyncClient, base: str, chave: str) -> list[str]:
    resposta = await cliente.get(
        f"{base}/models", headers={"Authorization": f"Bearer {chave}"}
    )
    resposta.raise_for_status()
    return [m["id"] for m in resposta.json().get("data", [])]


# A lista de modelo muda sem aviso, entao e descoberta na hora e guardada.
async def modelos() -> list[str]:
    global _modelos
    async with _tranca:
        if _modelos is not None:
            return _modelos
        encontrados: list[tuple[str, float]] = []
        async with httpx.AsyncClient(timeout=10) as cliente:
            for provedor, base, variavel in PROVEDORES:
                chave = os.environ.get(variavel)
                if not chave:
                    continue
                try:
                    for nome in await _listar(cliente, base, chave):
                        if any(x in nome.lower() for x in FORA):
                            continue
                        encontrados.append((f"{provedor}/{nome}", _porte(nome)))
                except httpx.HTTPError:
                    registro.warning("não foi possível listar modelos de %s", provedor)
        _modelos = [nome for nome, _ in sorted(encontrados, key=lambda x: -x[1])]
        return _modelos


# O import do litellm custa segundos, entao so acontece na primeira chamada.
async def _perguntar(mensagens: list[dict]) -> str | None:
    disponiveis = await modelos()
    if not disponiveis:
        return None

    import litellm
    from litellm import acompletion

    # Cada tentativa que falha despeja o traceback inteiro no log.
    litellm.suppress_debug_info = True
    logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

    try:
        resposta = await acompletion(
            model=disponiveis[0],
            messages=mensagens,
            fallbacks=disponiveis[1:],
            timeout=TEMPO_LIMITE,
            response_format=Sugestoes,
        )
        return resposta.choices[0].message.content
    except Exception:  # noqa: BLE001 - sugestao nunca pode derrubar o catalogo
        registro.warning("nenhum provedor respondeu")
        return None


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
    bruto = await _perguntar(
        [
            {"role": "system", "content": INSTRUCAO},
            {"role": "user", "content": json.dumps(pergunta, ensure_ascii=False)},
        ]
    )
    if not bruto:
        return {}

    # Coluna que nao veio na pergunta e alucinacao e nao entra.
    conhecidas = {c["coluna"] for c in campos}
    try:
        dados = Sugestoes.model_validate_json(bruto)
    except ValidationError:
        registro.warning("resposta do modelo fora do formato")
        return {}
    return {s.coluna: s for s in dados.colunas if s.coluna in conhecidas}
