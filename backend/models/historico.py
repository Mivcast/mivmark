from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class HistoricoMark(Base):
    __tablename__ = "historico_mark"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    data_hora = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="historico")
