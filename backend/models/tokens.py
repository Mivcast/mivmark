from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
from backend.database import Base
from datetime import datetime

class TokenAtivacao(Base):
    __tablename__ = "tokens_ativacao"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(TIMESTAMP, default=datetime.utcnow)  