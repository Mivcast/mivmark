from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker
from database import engine
from models import Arquivo, Usuario
from api.auth import get_current_user
from datetime import datetime
import os
import shutil

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

UPLOAD_DIR = "data/clientes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
def upload_arquivo(
    file: UploadFile = File(...),
    usuario: Usuario = Depends(get_current_user)
):
    db = SessionLocal()

    nome_arquivo = file.filename
    caminho_final = os.path.join(UPLOAD_DIR, f"{usuario.id}_{nome_arquivo}")

    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    novo = Arquivo(
        usuario_id=usuario.id,
        nome_arquivo=nome_arquivo,
        caminho_arquivo=caminho_final,
        tipo=file.content_type,
        data_upload=datetime.utcnow()
    )
    db.add(novo)
    db.commit()

    return {"mensagem": "Arquivo salvo com sucesso."}

@router.get("/arquivos")
def listar_arquivos(usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()
    arquivos = db.query(Arquivo).filter(Arquivo.usuario_id == usuario.id).all()
    return [
        {
            "nome": a.nome_arquivo,
            "tipo": a.tipo,
            "data_upload": a.data_upload,
            "caminho": a.caminho_arquivo
        }
        for a in arquivos
    ]
