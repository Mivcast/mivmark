from sqlalchemy import Column, Integer, String, ForeignKey, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class HistoricoMark(Base):
    __tablename__ = "historico_mark"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    remetente = Column(String)
    mensagem = Column(Text)
    data_envio = Column(TIMESTAMP, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="historico")
