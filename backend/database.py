from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Configuração do engine com pool otimizado para conexões
engine = create_engine(
    DATABASE_URL,
    pool_size=10,         # número máximo de conexões persistentes no pool
    max_overflow=20,      # conexões extras temporárias além do pool_size
    pool_timeout=30,      # tempo máximo (em segundos) para aguardar conexão disponível
    pool_pre_ping=True    # testa se a conexão está ativa antes de usar
)

# Sessão para ser usada nas rotas do FastAPI
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos ORM
Base = declarative_base()

# Dependência para injetar sessão no FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




