from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    descricao = Column(Text)
    capa_url = Column(String)
    categoria = Column(String)
    gratuito = Column(Boolean, default=True)
    preco = Column(Numeric, nullable=True)
    destaque = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    aulas = relationship("Aula", back_populates="curso", cascade="all, delete")
    compras = relationship("CompraCurso", back_populates="curso")


class Aula(Base):
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    titulo = Column(String)
    descricao = Column(Text)
    video_url = Column(String)
    ordem = Column(Integer)

    curso = relationship("Curso", back_populates="aulas")


class CompraCurso(Base):
    __tablename__ = "compras_cursos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    preco_pago = Column(Numeric)
    data_compra = Column(DateTime, default=datetime.utcnow)

    curso = relationship("Curso", back_populates="compras")


class ProgressoCurso(Base):
    __tablename__ = "progresso_cursos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    aula_id = Column(Integer, ForeignKey("aulas.id"))
    concluido_em = Column(DateTime, default=datetime.utcnow)


class CupomDesconto(Base):
    __tablename__ = "cupons"

    id = Column(Integer, primary_key=True)
    codigo = Column(String, unique=True)
    descricao = Column(String)
    percentual = Column(Numeric)  # Ex: 15.00 = 15%
    ativo = Column(Boolean, default=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True)  # Se for específico
    validade = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Afiliado(Base):
    __tablename__ = "afiliados"

    id = Column(Integer, primary_key=True)
    nome = Column(String)
    email = Column(String)
    codigo = Column(String, unique=True)  # Código de afiliado
    comissao_percentual = Column(Numeric)  # Ex: 10%
    criado_em = Column(DateTime, default=datetime.utcnow)


class PagamentoCurso(Base):
    __tablename__ = "pagamentos_cursos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    status = Column(String, default="pendente")  # pendente, pago, cancelado
    valor = Column(Numeric)
    metodo = Column(String)  # exemplo: "pix", "cartao"
    gateway = Column(String)  # exemplo: "infinitepay"
    codigo_externo = Column(String)  # ID do pagamento no gateway (ex: InfinitePay)
    criado_em = Column(DateTime, default=datetime.utcnow)
    confirmado_em = Column(DateTime, nullable=True)

    curso = relationship("Curso")


