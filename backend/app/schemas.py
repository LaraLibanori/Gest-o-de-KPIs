from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Nome = Field(min_length=1, max_length=120)


class Perfil(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    nome: str | None


class OrganizacaoIn(BaseModel):
    nome: str = Nome

    # min_length sozinho deixa passar "   ".
    @field_validator("nome")
    @classmethod
    def sem_espaco_sobrando(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("nome não pode ser vazio")
        return v


class Organizacao(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    criada_em: datetime
    papel: Literal["dono", "membro"]


class ConviteIn(BaseModel):
    email: EmailStr
    papel: Literal["dono", "membro"] = "membro"


class Convite(BaseModel):
    id: UUID | None
    email: str
    papel: Literal["dono", "membro"]
    situacao: Literal["membro", "pendente"]
    criado_em: datetime


class Membro(BaseModel):
    usuario_id: UUID
    email: str
    nome: str | None
    papel: Literal["dono", "membro"]
    criado_em: datetime


class ConexaoIn(BaseModel):
    nome: str = Nome
    host: str = Field(min_length=1, max_length=255)
    porta: int = Field(default=5432, ge=1, le=65535)
    banco: str = Field(min_length=1, max_length=120)
    usuario: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=1, max_length=255)
    tabela_fato: str | None = Field(default=None, max_length=120)

    @field_validator("nome", "host", "banco", "usuario")
    @classmethod
    def sem_espaco(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("campo obrigatório")
        return v


# A senha nunca sai daqui.
class Conexao(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    host: str
    porta: int
    banco: str
    usuario: str
    tabela_fato: str | None
    tabela_tipo: str | None
    descricao_negocio: str | None
    segmento: str | None
    etapa: str
    verificada_em: datetime | None
    verificacao_erro: str | None
    criada_em: datetime


class Relacao(BaseModel):
    nome: str
    tipo: Literal["tabela", "view", "view materializada"]


class Verificacao(BaseModel):
    ok: bool
    erro: str | None = None
    relacoes: list[Relacao] = []


class ConexaoEtapa(BaseModel):
    tabela_fato: str | None = Field(default=None, max_length=200)
    tabela_tipo: str | None = Field(default=None, max_length=40)
    descricao_negocio: str | None = Field(default=None, max_length=500)
    segmento: str | None = Field(default=None, max_length=40)
    etapa: Literal["tabela", "negocio", "catalogo", "indicadores", "pronta"] | None = (
        None
    )


class Campo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coluna: str
    tipo: str
    cardinalidade: int | None
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"]
    rotulo: str | None
    confirmado: bool
    ordem: int


class Sugestao(BaseModel):
    aplicadas: int
    campos: list["Campo"]


class CampoIn(BaseModel):
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"] | None = None
    rotulo: str | None = Field(default=None, max_length=120)
    confirmado: bool | None = None


AGREGACAO = Literal["soma", "media", "contagem", "distintos", "minimo", "maximo"]
PERIODO = Literal[
    "sempre", "ultimos_7_dias", "ultimos_30_dias", "ultimos_90_dias", "ano_atual"
]


class Segmento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chave: str
    nome: str


class Indicador(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    agregacao: AGREGACAO
    coluna: str | None
    dimensao: str | None
    tempo: str | None
    periodo: PERIODO | None
    origem: Literal["regra", "segmento", "manual"]
    confirmado: bool
    ordem: int


class IndicadorIn(BaseModel):
    nome: str = Field(max_length=120)
    agregacao: AGREGACAO
    coluna: str | None = Field(default=None, max_length=200)
    dimensao: str | None = Field(default=None, max_length=200)
    tempo: str | None = Field(default=None, max_length=200)
    periodo: PERIODO | None = None


class IndicadorEdicao(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    agregacao: AGREGACAO | None = None
    coluna: str | None = Field(default=None, max_length=200)
    dimensao: str | None = Field(default=None, max_length=200)
    tempo: str | None = Field(default=None, max_length=200)
    periodo: PERIODO | None = None
    confirmado: bool | None = None


class Descartado(BaseModel):
    nome: str
    motivo: str


class Proposta(BaseModel):
    segmento: str | None
    indicadores: list[Indicador]
    descartados: list[Descartado] = []
