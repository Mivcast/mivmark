# backend/models/cupons.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from backend.database import Base

class CupomDesconto(Base):
    __tablename__ = "cupons_desconto"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)

    # "percentual" ou "valor_fixo"
    tipo_valor = Column(String(20), nullable=False, default="percentual")
    valor = Column(Float, nullable=False, default=0.0)

    # "plano", "curso", "aplicativo" ou "todos"
    tipo_aplicacao = Column(String(20), nullable=False, default="todos")

    # opcionalmente amarrar a um item específico
    plano_nome = Column(String(50), nullable=True)
    curso_id = Column(Integer, nullable=True)
    aplicativo_id = Column(Integer, nullable=True)

    # controle de uso
    limite_uso_total = Column(Integer, nullable=True)  # None = ilimitado
    usos_realizados = Column(Integer, nullable=False, default=0)

    # datas
    criado_em = Column(DateTime, default=datetime.utcnow)
    valido_ate = Column(DateTime, nullable=True)  # None = sem validade

    ativo = Column(Boolean, default=True)
    observacoes = Column(String(255), nullable=True)


# ---------------- Pydantic Schemas ----------------

class CupomBase(BaseModel):
    codigo: str
    tipo_valor: str = "percentual"
    valor: float = 0.0
    tipo_aplicacao: str = "todos"
    plano_nome: Optional[str] = None
    curso_id: Optional[int] = None
    aplicativo_id: Optional[int] = None
    limite_uso_total: Optional[int] = None
    valido_ate: Optional[datetime] = None
    ativo: bool = True
    observacoes: Optional[str] = None

class CupomCreate(CupomBase):
    pass

class CupomSchema(CupomBase):
    id: int
    usos_realizados: int
    criado_em: datetime

    class Config:
        orm_mode = True
