# backend/models/senha_reset.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from datetime import datetime
from backend.database import Base


class SenhaResetToken(Base):
    __tablename__ = "senha_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # Guardamos email para simplificar (pode virar FK depois se quiser)
    email = Column(String, index=True, nullable=False)

    # Não salva o código puro, só o hash
    codigo_hash = Column(String, nullable=False)

    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


Index("ix_senha_reset_email_used", SenhaResetToken.email, SenhaResetToken.used)
