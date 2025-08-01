from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.agenda import EventoAgenda, TipoEventoEnum, PrioridadeEnum, OrigemEventoEnum
from datetime import datetime
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/agenda", tags=["Agenda"])

# 🔵 MODELOS Pydantic
class EventoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    data_inicio: datetime
    data_fim: datetime
    tipo_evento: TipoEventoEnum = TipoEventoEnum.outro
    prioridade: PrioridadeEnum = PrioridadeEnum.media
    origem: OrigemEventoEnum = OrigemEventoEnum.manual
    recorrencia: Optional[str] = None
    visivel_cliente: bool = False
    usuario_id: int

class EventoOut(BaseModel):
    id: UUID
    titulo: str
    descricao: Optional[str]
    data_inicio: datetime
    data_fim: datetime
    tipo_evento: TipoEventoEnum
    prioridade: PrioridadeEnum
    origem: OrigemEventoEnum
    visivel_cliente: bool
    criado_em: datetime

    class Config:
        from_attributes = True  # Pydantic v2: substitui orm_mode

# 🔵 ROTAS FastAPI
@router.post("/", response_model=EventoOut)
def criar_evento(evento: EventoCreate, db: Session = Depends(get_db)):
    novo_evento = EventoAgenda(**evento.dict())
    db.add(novo_evento)
    db.commit()
    db.refresh(novo_evento)
    return novo_evento

@router.get("/{usuario_id}", response_model=List[EventoOut])
def listar_eventos(usuario_id: int, db: Session = Depends(get_db)):
    eventos = db.query(EventoAgenda).filter_by(usuario_id=usuario_id).order_by(EventoAgenda.data_inicio).all()
    return eventos

@router.put("/{evento_id}", response_model=EventoOut)
def atualizar_evento(evento_id: UUID, evento: EventoCreate, db: Session = Depends(get_db)):
    db_evento = db.query(EventoAgenda).filter_by(id=evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    for key, value in evento.dict().items():
        setattr(db_evento, key, value)

    db.commit()
    db.refresh(db_evento)
    return db_evento

@router.delete("/{evento_id}")
def deletar_evento(evento_id: UUID, db: Session = Depends(get_db)):
    db_evento = db.query(EventoAgenda).filter_by(id=evento_id).first()
    if not db_evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    
    db.delete(db_evento)
    db.commit()
    return {"ok": True, "mensagem": "Evento excluído com sucesso"}
