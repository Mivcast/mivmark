from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean, ForeignKey, Numeric, JSON, DateTime
from sqlalchemy.orm import relationship
from ..database import Base
from .tokens import TokenAtivacao
from .demo import CadastroDemo
from .historico_mark import HistoricoMark
from .marketing import CardMarketing
from datetime import datetime

class Diagnostico(Base):
    __tablename__ = "diagnosticos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    data_avaliacao = Column(TIMESTAMP, default=datetime.utcnow)
    nota_geral = Column(String)
    respostas = Column(JSON)

    usuario = relationship("Usuario", back_populates="diagnosticos")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    tipo_usuario = Column(String, default="cliente")
    plano_atual = Column(String)
    data_criacao = Column(TIMESTAMP)
    nota_saude = Column(String, nullable=True)  # ✅ Nova coluna para salvar a nota do diagnóstico
    respostas_saude = Column(JSON, nullable=True)  # ⬅️ Adicione abaixo de nota_saude



    empresa = relationship("Empresa", back_populates="usuario", uselist=False)
    historico = relationship("HistoricoMark", back_populates="usuario", cascade="all, delete-orphan")
    consultoria = relationship("Consultoria", back_populates="usuario", uselist=False)
    diagnosticos = relationship("Diagnostico", back_populates="usuario", cascade="all, delete-orphan")


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    nome_empresa = Column(String)
    cnpj = Column(String)
    rua = Column(String)
    numero = Column(String)
    bairro = Column(String)
    cidade = Column(String)
    cep = Column(String)
    logo_url = Column(String, nullable=True)
    descricao = Column(Text)
    nicho = Column(String)
    funcionarios = Column(JSON)
    produtos = Column(JSON)
    redes_sociais = Column(JSON)
    informacoes_adicionais = Column(Text)
    atualizado_em = Column(TIMESTAMP)

    usuario = relationship("Usuario", back_populates="empresa")


class Arquivo(Base):
    __tablename__ = "arquivos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    nome_arquivo = Column(String)
    caminho_arquivo = Column(String)
    tipo = Column(String)
    data_upload = Column(TIMESTAMP)



class Consultoria(Base):
    __tablename__ = "consultorias"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    etapa_atual = Column(String)
    etapas_concluidas = Column(JSON)
    progresso = Column(JSON, default={})  # Ex: { "1": {"concluido": True, "checklist": [True, False, True]} }
    data_inicio = Column(TIMESTAMP)

    usuario = relationship("Usuario", back_populates="consultoria")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    plano = Column(String)
    valor = Column(Numeric)
    status = Column(String)
    gateway = Column(String)
    data_pagamento = Column(TIMESTAMP)


class Orcamento(Base):
    __tablename__ = "orcamentos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    dados_cliente = Column(JSON)
    itens = Column(JSON)
    texto_orcamento = Column(Text)
    gerado_em = Column(TIMESTAMP)
