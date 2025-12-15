# backend/models/consultor_mensal.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class ConsultorMensal(Base):
    __tablename__ = "consultor_mensal"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    mes_ano = Column(String, nullable=False, index=True)  # YYYY-MM
    conteudo = Column(JSON, nullable=False, default=dict)

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow)

    # se você já tem relationship em Usuario/Empresa, ok.
    # usuario = relationship("Usuario")
    # empresa = relationship("Empresa")
