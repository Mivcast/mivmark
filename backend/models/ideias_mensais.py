# backend/models/ideias_mensais.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class IdeiasMensais(Base):
    __tablename__ = "ideias_mensais"

    id = Column(Integer, primary_key=True, index=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)

    mes_ano = Column(String, nullable=False)  # formato: YYYY-MM
    setor = Column(String, nullable=True)

    conteudo = Column(JSON, nullable=False)  
    # JSON com categorias, cards, conteúdos, branding, favoritos etc.

    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    empresa = relationship("Empresa")

    __table_args__ = (
        UniqueConstraint("empresa_id", "mes_ano", name="uq_empresa_mes"),
    )
