from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Dict
from database import engine
from models import Consultoria, Usuario
from api.auth import get_current_user
from datetime import datetime

router = APIRouter()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Schemas
class TarefaChecklist(BaseModel):
    checklist: List[bool]
    concluido: bool

class ProgressoSchema(BaseModel):
    progresso: Dict[str, TarefaChecklist]  # 👈 Corrigido: chaves como string para compatibilidade com JSONField

class ConsultoriaSchema(BaseModel):
    etapa_atual: str
    etapas_concluidas: List[str] = []

# Iniciar consultoria
@router.post("/consultoria/iniciar")
def iniciar_consultoria(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    consultoria = db.query(Consultoria).filter(Consultoria.usuario_id == usuario.id).first()

    if consultoria:
        db.close()
        raise HTTPException(status_code=400, detail="Consultoria já iniciada.")

    nova = Consultoria(
        usuario_id=usuario.id,
        etapa_atual="Diagnóstico Inicial",
        etapas_concluidas=[],
        progresso={},
        data_inicio=datetime.now()
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    db.close()
    return {"mensagem": "Consultoria iniciada com sucesso!"}

# Atualizar progresso completo
@router.put("/consultoria/progresso")
def atualizar_progresso(dados: ProgressoSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        consultoria = db.query(Consultoria).filter(Consultoria.usuario_id == usuario.id).first()
        if not consultoria:
            raise HTTPException(status_code=404, detail="Consultoria não encontrada.")
        
        # Salvar como dicionário puro
        consultoria.progresso = {str(k): v.dict() for k, v in dados.progresso.items()}
        db.commit()
        return {"mensagem": "Progresso atualizado com sucesso."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Consultar progresso completo
@router.get("/consultoria/progresso")
def consultar_progresso(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        consultoria = db.query(Consultoria).filter(Consultoria.usuario_id == usuario.id).first()
        if not consultoria:
            raise HTTPException(status_code=404, detail="Consultoria não iniciada.")
        return consultoria.progresso or {}
    finally:
        db.close()

# Consultar status geral da consultoria
@router.get("/consultoria")
def consultar_consultoria(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        consultoria = db.query(Consultoria).filter(Consultoria.usuario_id == usuario.id).first()
        if not consultoria:
            raise HTTPException(status_code=404, detail="Consultoria não iniciada.")
        return {
            "etapa_atual": consultoria.etapa_atual,
            "etapas_concluidas": consultoria.etapas_concluidas,
            "data_inicio": consultoria.data_inicio
        }
    finally:
        db.close()

# Atualizar etapa atual
@router.put("/consultoria/etapa")
def atualizar_etapa(dados: ConsultoriaSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        consultoria = db.query(Consultoria).filter(Consultoria.usuario_id == usuario.id).first()
        if not consultoria:
            raise HTTPException(status_code=404, detail="Consultoria não encontrada.")
        
        consultoria.etapa_atual = dados.etapa_atual
        consultoria.etapas_concluidas = dados.etapas_concluidas
        db.commit()
        return {"mensagem": "Etapa da consultoria atualizada com sucesso."}
    finally:
        db.close()
