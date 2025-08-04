from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class Aplicativo(Base):
    __tablename__ = "aplicativos"

    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    descricao = Column(Text)
    icone_url = Column(String)
    categoria = Column(String)
    gratuito = Column(Boolean, default=True)
    preco = Column(Numeric, nullable=True)
    destaque = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    compras = relationship("CompraApp", back_populates="aplicativo")


class CompraApp(Base):
    __tablename__ = "compras_apps"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    app_id = Column(Integer, ForeignKey("aplicativos.id"))
    preco_pago = Column(Numeric)
    data_compra = Column(DateTime, default=datetime.utcnow)

    aplicativo = relationship("Aplicativo", back_populates="compras")


class AplicativoSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str]
    icone_url: Optional[str]
    categoria: Optional[str]
    gratuito: bool
    preco: float
    destaque: Optional[bool]
    ativo: Optional[bool]
    criado_em: Optional[datetime]

    class Config:
        orm_mode = True


