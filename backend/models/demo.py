from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base
from datetime import datetime

class CadastroDemo(Base):
    __tablename__ = "cadastros_demo"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    setor = Column(String, nullable=False)  # exemplo: "marketing", "vendas", etc.
    data_cadastro = Column(DateTime, default=datetime.utcnow)
