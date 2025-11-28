from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from backend.database import engine
from backend.models import Orcamento, Usuario
from backend.api.auth import get_current_user
from datetime import datetime
from typing import List, Dict

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

class OrcamentoSchema(BaseModel):
    dados_cliente: Dict
    itens: List[Dict]
    texto_orcamento: str

@router.post("/orcamento")
def criar_orcamento(dados: OrcamentoSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()

    novo = Orcamento(
        usuario_id=usuario.id,
        dados_cliente=dados.dados_cliente,
        itens=dados.itens,
        texto_orcamento=dados.texto_orcamento,
        gerado_em=datetime.utcnow()
    )
    db.add(novo)
    db.commit()
    db.close()
    return {"mensagem": "Orçamento criado com sucesso!"}

@router.get("/orcamento")
def listar_orcamentos(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    orcamentos = db.query(Orcamento).filter(Orcamento.usuario_id == usuario.id).all()
    db.close()

    return [
        {
            "id": o.id,
            "dados_cliente": o.dados_cliente,
            "itens": o.itens,
            "texto_orcamento": o.texto_orcamento,
            "gerado_em": o.gerado_em
        }
        for o in orcamentos
    ]
