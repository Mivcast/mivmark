# backend/models/planos.py
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON
from database import Base
from pydantic import BaseModel
from typing import Optional, List

class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    descricao = Column(String)
    preco_mensal = Column(Float)
    preco_anual = Column(Float)
    modulos_liberados = Column(JSON)  # lista de strings: ["empresa", "orcamento", ...]
    bonus = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)

# ----------- Pydantic Schemas -----------
class PlanoSchema(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    preco_mensal: float
    preco_anual: float
    modulos_liberados: List[str]
    bonus: Optional[str]
    ativo: bool

    class Config:
        orm_mode = True

class PlanoCreate(BaseModel):
    nome: str
    descricao: Optional[str]
    preco_mensal: float
    preco_anual: float
    modulos_liberados: List[str]
    bonus: Optional[str]
    ativo: bool = True
