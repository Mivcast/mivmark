from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from database import Base
import enum

class TipoEventoEnum(str, enum.Enum):
    reuniao = "Reunião"
    tarefa = "Tarefa"
    evento = "Evento"
    campanha = "Campanha"
    outro = "Outro"

class PrioridadeEnum(str, enum.Enum):
    baixa = "Baixa"
    media = "Média"
    alta = "Alta"

class OrigemEventoEnum(str, enum.Enum):
    manual = "Manual"
    sistema = "Sistema"
    google = "Google"
    cliente = "Cliente"

class EventoAgenda(Base):
    __tablename__ = "eventos_agenda"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)  # ← Corrigido

    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=True)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)

    tipo_evento = Column(Enum(TipoEventoEnum), default=TipoEventoEnum.outro)
    prioridade = Column(Enum(PrioridadeEnum), default=PrioridadeEnum.media)
    origem = Column(Enum(OrigemEventoEnum), default=OrigemEventoEnum.manual)

    recorrencia = Column(String, nullable=True)
    visivel_cliente = Column(Boolean, default=False)

    criado_em = Column(DateTime, default=datetime.utcnow)
