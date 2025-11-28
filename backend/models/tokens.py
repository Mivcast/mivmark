from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime, timedelta

class TokenAtivacao(Base):
    __tablename__ = "tokens_ativacao"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(TIMESTAMP, default=datetime.utcnow)

    # 🔥 Campos adicionados
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    plano = Column(String, nullable=True)  # ex: "consultoria_full"
    expira_em = Column(DateTime, nullable=True)

    usuario = relationship("Usuario", backref="tokens")

    @staticmethod
    def gerar_token(usuario_id: int, plano: str, dias_validade: int = 365):
        import secrets
        novo_token = secrets.token_hex(16)

        return TokenAtivacao(
            token=novo_token,
            usuario_id=usuario_id,
            plano=plano,
            expira_em=datetime.utcnow() + timedelta(days=dias_validade),
            ativo=True
        )
