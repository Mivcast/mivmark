from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from database import engine
from models import HistoricoMark, Usuario
from api.auth import get_current_user
from datetime import datetime
from typing import List

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

class MensagemSchema(BaseModel):
    remetente: str  # 'usuario' ou 'mark'
    mensagem: str

@router.post("/historico")
def salvar_mensagem(dados: MensagemSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()

    nova = HistoricoMark(
        usuario_id=usuario.id,
        remetente=dados.remetente,
        mensagem=dados.mensagem,
        data_envio=datetime.utcnow()
    )
    db.add(nova)
    db.commit()
    db.close()
    return {"mensagem": "Mensagem registrada no histórico."}

@router.get("/historico")
def obter_historico(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    mensagens = db.query(HistoricoMark).filter(HistoricoMark.usuario_id == usuario.id).order_by(HistoricoMark.data_envio).all()
    db.close()

    return [
        {
            "remetente": m.remetente,
            "mensagem": m.mensagem,
            "data_envio": m.data_envio
        }
        for m in mensagens
    ]
