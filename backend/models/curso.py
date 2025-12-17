# backend/models/curso.py

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=True)
    capa_url = Column(String, nullable=True)
    categoria = Column(String, nullable=True)

    gratuito = Column(Boolean, default=True)
    preco = Column(Numeric, nullable=True)

    destaque = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)

    # ✅ você usa isso no admin, então precisa existir no model
    ordem = Column(Integer, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)

    aulas = relationship("Aula", back_populates="curso", cascade="all, delete-orphan")
    compras = relationship("CompraCurso", back_populates="curso", cascade="all, delete-orphan")

    # ✅ cupons vêm do backend/models/cupom.py (não crie outra classe aqui)
    cupons = relationship("CupomDesconto", back_populates="curso")


class Aula(Base):
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)

    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    ordem = Column(Integer, nullable=True)

    curso = relationship("Curso", back_populates="aulas")


class CompraCurso(Base):
    __tablename__ = "compras_cursos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)

    preco_pago = Column(Numeric, nullable=False, default=0)
    data_compra = Column(DateTime, default=datetime.utcnow)

    curso = relationship("Curso", back_populates="compras")


class ProgressoCurso(Base):
    __tablename__ = "progresso_cursos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    aula_id = Column(Integer, ForeignKey("aulas.id"), nullable=False)

    concluido_em = Column(DateTime, default=datetime.utcnow)


class Afiliado(Base):
    __tablename__ = "afiliados"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    codigo = Column(String, unique=True, index=True, nullable=False)  # Código de afiliado
    comissao_percentual = Column(Numeric, nullable=False, default=0)  # Ex: 10%
    criado_em = Column(DateTime, default=datetime.utcnow)


class PagamentoCurso(Base):
    __tablename__ = "pagamentos_cursos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)

    status = Column(String, default="pendente")  # pendente, pago, cancelado
    valor = Column(Numeric, nullable=False, default=0)

    metodo = Column(String, nullable=True)   # "pix", "cartao"
    gateway = Column(String, nullable=True)  # "infinitepay"
    codigo_externo = Column(String, nullable=True)  # ID no gateway

    criado_em = Column(DateTime, default=datetime.utcnow)
    confirmado_em = Column(DateTime, nullable=True)

    curso = relationship("Curso")
