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
    esquema: str | None = Field(default=None, max_length=63)
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

    @field_validator("esquema")
    @classmethod
    def esquema_ou_nada(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class ConexaoProva(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    porta: int = Field(default=5432, ge=1, le=65535)
    banco: str = Field(min_length=1, max_length=120)
    esquema: str | None = Field(default=None, max_length=63)
    usuario: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=1, max_length=255)

    @field_validator("host", "banco", "usuario")
    @classmethod
    def sem_espaco(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("campo obrigatório")
        return v

    @field_validator("esquema")
    @classmethod
    def esquema_ou_nada(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


# A senha nunca sai daqui.
class Conexao(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    host: str
    porta: int
    banco: str
    esquema: str | None
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
    esquemas: list[str] = []


class ConexaoPatch(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    host: str | None = Field(default=None, max_length=255)
    porta: int | None = Field(default=None, ge=1, le=65535)
    banco: str | None = Field(default=None, max_length=120)
    esquema: str | None = Field(default=None, max_length=63)
    usuario: str | None = Field(default=None, max_length=120)
    senha: str | None = Field(default=None, max_length=255)
    tabela_fato: str | None = Field(default=None, max_length=200)
    tabela_tipo: str | None = Field(default=None, max_length=40)
    descricao_negocio: str | None = Field(default=None, max_length=500)
    segmento: str | None = Field(default=None, max_length=40)
    etapa: Literal["tabela", "negocio", "catalogo", "indicadores", "pronta"] | None = (
        None
    )

    @field_validator("nome", "host", "banco", "usuario")
    @classmethod
    def sem_espaco(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None

    @field_validator("esquema")
    @classmethod
    def esquema_ou_nada(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None

    @property
    def credenciais(self) -> dict:
        campos = ("host", "porta", "banco", "esquema", "usuario")
        return {c: getattr(self, c) for c in campos if c in self.model_fields_set}


class Campo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    coluna: str
    tipo: str
    cardinalidade: int | None
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"]
    rotulo: str | None
    formula: str | None = None
    confirmado: bool
    ordem: int
    # Quantos indicadores apontam para esta coluna: apagar pode quebrar o painel.
    em_uso: int = 0


class CampoCalculadoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=60, pattern=r"^[a-z_][a-z0-9_]*$")
    rotulo: str = Field(min_length=1, max_length=120)
    formula: str = Field(min_length=1, max_length=400)
    papel: Literal["metrica", "dimensao"] = "metrica"


class CampoCalculadoPatch(BaseModel):
    rotulo: str | None = Field(default=None, max_length=120)
    formula: str | None = Field(default=None, max_length=400)
    papel: Literal["metrica", "dimensao"] | None = None


class Sugestao(BaseModel):
    aplicadas: int
    campos: list["Campo"]


class CampoIn(BaseModel):
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"] | None = None
    rotulo: str | None = Field(default=None, max_length=120)
    confirmado: bool | None = None


AGREGACAO = Literal["soma", "media", "contagem", "distintos", "minimo", "maximo"]
GRAFICO = Literal["numero", "barra", "linha", "pizza", "tabela"]
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
    grafico: GRAFICO
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
    grafico: GRAFICO | None = None


class IndicadorEdicao(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    agregacao: AGREGACAO | None = None
    coluna: str | None = Field(default=None, max_length=200)
    dimensao: str | None = Field(default=None, max_length=200)
    tempo: str | None = Field(default=None, max_length=200)
    periodo: PERIODO | None = None
    grafico: GRAFICO | None = None
    confirmado: bool | None = None


class Descartado(BaseModel):
    nome: str
    motivo: str


class Proposta(BaseModel):
    segmento: str | None
    indicadores: list[Indicador]
    descartados: list[Descartado] = []


class Quebra(BaseModel):
    rotulo: str
    valor: float | None


JANELA = Literal["7d", "30d", "90d", "12m", "tudo"]


class IndicadorCalculado(Indicador):
    valor: float | None = None
    anterior: float | None = None
    variacao: float | None = None
    serie: list[Quebra] = []
    erro: str | None = None


class Dimensao(BaseModel):
    coluna: str
    rotulo: str


class Composicao(BaseModel):
    coluna: str
    rotulo: str
    total: float | None = None
    pontos: list[Quebra] = []


class Painel(BaseModel):
    tabela: str | None
    janela: JANELA
    indicadores: list[IndicadorCalculado] = []
    dimensoes: list[Dimensao] = []
    # Falso sem coluna de data: o filtro de periodo nao teria efeito.
    janelavel: bool = True
    erro: str | None = None
    avisos: list[str] = []


class SugestaoGrafico(BaseModel):
    aplicadas: int
    indicadores: list[Indicador]


class DashboardIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=200)


class DashboardPatch(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=80)
    descricao: str | None = Field(default=None, max_length=200)


class ItemDashboard(IndicadorCalculado):
    # Sem isso a tela nao sabe de qual conexao o indicador veio.
    conexao_id: UUID
    conexao: str


class Dashboard(BaseModel):
    id: UUID
    nome: str
    descricao: str | None = None
    criado_em: datetime
    indicadores: list[ItemDashboard] = []
    conexoes: list[str] = []


class DashboardIndicadoresIn(BaseModel):
    indicadores: list[UUID] = Field(default_factory=list, max_length=40)
