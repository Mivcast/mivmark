from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from database import engine
from models import Pagamento, Usuario
from models.curso import PagamentoCurso, CompraCurso
from api.auth import get_current_user
from datetime import datetime

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

# ------------------- Pagamentos de Plano -------------------

class PagamentoSchema(BaseModel):
    plano: str
    valor: float
    status: str
    gateway: str

@router.post("/pagamento")
def registrar_pagamento(dados: PagamentoSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    novo = Pagamento(
        usuario_id=usuario.id,
        plano=dados.plano,
        valor=dados.valor,
        status=dados.status,
        gateway=dados.gateway,
        data_pagamento=datetime.utcnow()
    )
    db.add(novo)
    db.commit()
    db.close()
    return {"mensagem": "Pagamento registrado com sucesso!"}

@router.get("/pagamento")
def listar_pagamentos(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    pagamentos = db.query(Pagamento).filter(Pagamento.usuario_id == usuario.id).all()
    db.close()
    return [
        {
            "plano": p.plano,
            "valor": p.valor,
            "status": p.status,
            "gateway": p.gateway,
            "data_pagamento": p.data_pagamento
        }
        for p in pagamentos
    ]

# ------------------- Confirmação de Curso -------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/confirmar")
def confirmar_pagamento(
    pagamento_id: int = Body(...),
    codigo_externo: str = Body(...),
    db: Session = Depends(get_db)
):
    pagamento = db.query(PagamentoCurso).filter_by(id=pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado.")
    if pagamento.status == "pago":
        return {"mensagem": "Pagamento já confirmado."}

    pagamento.status = "pago"
    pagamento.codigo_externo = codigo_externo
    pagamento.confirmado_em = datetime.utcnow()

    compra = CompraCurso(
        usuario_id=pagamento.usuario_id,
        curso_id=pagamento.curso_id,
        preco_pago=pagamento.valor
    )
    db.add(compra)
    db.commit()

    return {"mensagem": "Pagamento confirmado e curso liberado com sucesso!"}
