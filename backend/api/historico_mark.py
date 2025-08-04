from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from backend.database import engine
from backend.models import HistoricoMark, Usuario
from backend.api.auth import get_current_user
from datetime import datetime

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

class MensagemSchema(BaseModel):
    remetente: str  # "usuário" ou "mark"
    mensagem: str

@router.post("/historico")
def salvar_mensagem(dados: MensagemSchema, usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()

    nova = HistoricoMark(
        usuario_id=usuario.id,
        remetente=dados.remetente,
        mensagem=dados.mensagem,
        data_envio=datetime.utcnow()
    )

    db.add(nova)
    db.commit()

    return {"mensagem": "Mensagem registrada no histórico."}

@router.get("/historico")
def listar_historico(usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()
    historico = db.query(HistoricoMark).filter(HistoricoMark.usuario_id == usuario.id).order_by(HistoricoMark.data_envio).all()

    return [
        {
            "remetente": h.remetente,
            "mensagem": h.mensagem,
            "data_envio": h.data_envio
        }
        for h in historico
    ]
