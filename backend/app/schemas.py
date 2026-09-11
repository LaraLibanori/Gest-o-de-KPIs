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


# Convidar quem ja tem conta vira membro na hora; quem nao tem fica pendente.
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
    etapa: Literal["tabela", "negocio", "catalogo", "pronta"] | None = None


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


class CampoIn(BaseModel):
    papel: Literal["metrica", "dimensao", "tempo", "ignorar"] | None = None
    rotulo: str | None = Field(default=None, max_length=120)
    confirmado: bool | None = None
