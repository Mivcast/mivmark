# backend/models/cupom.py

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class CupomDesconto(Base):
    __tablename__ = "cupons_desconto"

    id = Column(Integer, primary_key=True, index=True)

    codigo = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(Text, nullable=True)

    # Percentual (mantido por compatibilidade com o que você já usa)
    desconto_percent = Column(Numeric, nullable=True)

    # "plano" | "curso" | "aplicativo"
    escopo = Column(String, nullable=True)

    # Alvos
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=True)
    aplicativo_id = Column(Integer, ForeignKey("aplicativos.id"), nullable=True)

    # IMPORTANTE: no seu banco é plano_nome (não plano_id)
    plano_nome = Column(String, nullable=True)

    # Datas/status
    valido_ate = Column(DateTime, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)

    observacoes = Column(String, nullable=True)

    # ----------------------------
    # Campos que EXISTEM no seu banco e estão NOT NULL
    # (pelo erro: tipo_valor é NOT NULL)
    # ----------------------------
    # Sugestão de padrão:
    # - tipo_valor: "percent" | "fixo"
    # - valor: valor numérico do cupom (ex.: 10 = 10% ou R$10)
    # - tipo_aplicacao: "desconto" (futuro: "cashback" etc.)
    # - limite_uso_total: quantas vezes pode usar (None = infinito)
    # - usos_realizados: contador
    tipo_valor = Column(String, nullable=False, default="percent")
    valor = Column(Numeric, nullable=False, default=0)
    tipo_aplicacao = Column(String, nullable=False, default="desconto")
    limite_uso_total = Column(Integer, nullable=True)
    usos_realizados = Column(Integer, nullable=False, default=0)

    # Relacionamentos (agora com FK, não dá mais erro de mapper)
    curso = relationship("Curso", back_populates="cupons")
    aplicativo = relationship("Aplicativo", primaryjoin="CupomDesconto.aplicativo_id==Aplicativo.id", viewonly=True)
