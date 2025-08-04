from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class CardMarketing(Base):
    __tablename__ = "cards_marketing"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    titulo = Column(String)
    descricao = Column(Text)
    fonte = Column(String)  # URL da matéria
    ideias_conteudo = Column(Text)  # Texto com até 3 ideias separadas por quebra de linha
    tipo = Column(String)  # ex: "Tendência", "Promoção", "Produto em Alta"
    mes_referencia = Column(String)  # formato: "2025-06"
    favorito = Column(Boolean, default=False)
    eh_atualizacao = Column(Boolean, default=False)
    criado_em = Column(TIMESTAMP, default=datetime.utcnow)
    atualizado_em = Column(TIMESTAMP, default=datetime.utcnow)

    usuario = relationship("Usuario", backref="cards_marketing")
