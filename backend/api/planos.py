# backend/api/planos.py (novo endpoint para gerenciar planos)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.planos import Plano, PlanoSchema, PlanoCreate

router = APIRouter(prefix="/planos", tags=["Planos"])

@router.get("/", response_model=list[PlanoSchema])
def listar_planos(db: Session = Depends(get_db)):
    return db.query(Plano).all()

@router.post("/", response_model=PlanoSchema)
def criar_plano(plano: PlanoCreate, db: Session = Depends(get_db)):
    novo = Plano(**plano.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@router.put("/{plano_id}", response_model=PlanoSchema)
def atualizar_plano(plano_id: int, plano: PlanoCreate, db: Session = Depends(get_db)):
    db_plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not db_plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    for campo, valor in plano.dict().items():
        setattr(db_plano, campo, valor)
    db.commit()
    db.refresh(db_plano)
    return db_plano

@router.delete("/{plano_id}")
def excluir_plano(plano_id: int, db: Session = Depends(get_db)):
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    db.delete(plano)
    db.commit()
    return {"ok": True}
