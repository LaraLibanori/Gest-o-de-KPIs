from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DashboardIn(BaseModel):
    nome: str


class Dashboard(BaseModel):
    id: UUID
    nome: str
    criado_em: datetime


class IndicadorIn(BaseModel):
    nome: str
    fonte: str
    coluna: str | None = None
    agregacao: Literal["count", "sum", "avg", "min", "max"]


class Indicador(BaseModel):
    id: UUID
    dashboard_id: UUID
    nome: str
    fonte: str
    coluna: str | None
    agregacao: str


class Valor(BaseModel):
    indicador_id: UUID
    nome: str
    valor: float | None
