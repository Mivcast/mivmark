# backend/api/historico_mark.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.models import HistoricoMark, Usuario
from backend.api.auth import get_usuario_logado  # mesmo usado em usuario.py



router = APIRouter(
    prefix="/mark",
    tags=["MARK - Histórico"]
)


class MensagemHistoricoIn(BaseModel):
    remetente: str  # "usuario" ou "mark"
    mensagem: str


class MensagemHistoricoOut(BaseModel):
    remetente: str
    mensagem: str
    data_envio: Optional[datetime] = None  # ⬅️ agora pode ser None

    class Config:
        orm_mode = True



@router.post("/historico")
def salvar_mensagem_historico(
    dados: MensagemHistoricoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """
    Salva uma mensagem no histórico do usuário logado.
    """
    remetente = (dados.remetente or "").strip().lower()
    if remetente not in ("usuario", "mark"):
        raise HTTPException(status_code=400, detail="Remetente inválido.")

    registro = HistoricoMark(
        usuario_id=usuario.id,
        remetente=remetente,
        mensagem=dados.mensagem,
        data_envio=datetime.utcnow(),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return {"status": "ok", "id": registro.id}


@router.get("/historico", response_model=List[MensagemHistoricoOut])
def obter_historico(
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """
    Retorna o histórico do MARK para o usuário logado.
    - Se 'busca' vier preenchido, filtra pela mensagem.
    """
    query = db.query(HistoricoMark).filter(HistoricoMark.usuario_id == usuario.id)

    if busca:
        like = f"%{busca}%"
        query = query.filter(HistoricoMark.mensagem.ilike(like))

    mensagens = (
        query.order_by(HistoricoMark.data_envio.desc())
        .limit(200)
        .all()
    )

    return mensagens
