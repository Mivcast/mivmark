from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.aplicativo import Aplicativo, CompraApp, AplicativoSchema
from models import Usuario
from api.auth import get_current_user
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import status

router = APIRouter(prefix="/aplicativos", tags=["Aplicativos"])

# ---------- MODELO PARA CRIAÇÃO ----------
class AplicativoCreate(BaseModel):
    titulo: str
    descricao: Optional[str]
    icone_url: Optional[str]
    categoria: Optional[str]
    gratuito: bool
    preco: Optional[float] = 0.0
    destaque: Optional[bool] = False
    ativo: Optional[bool] = True


# ---------- LISTAGEM PÚBLICA ----------
@router.get("/admin/listar_todos", response_model=List[AplicativoSchema])
def listar_todos_admin(db: Session = Depends(get_db)):
    return db.query(Aplicativo).order_by(Aplicativo.id.desc()).all()


# ---------- DETALHE DE UM APP ----------
@router.get("/{app_id}")
def detalhe_aplicativo(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Aplicativo).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Aplicativo não encontrado")
    return app


# ---------- COMPRA ----------
@router.post("/{app_id}/comprar")
def comprar_aplicativo(app_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    app = db.query(Aplicativo).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App não encontrado")

    if app.gratuito:
        raise HTTPException(status_code=400, detail="Este app é gratuito")

    ja_comprado = db.query(CompraApp).filter_by(usuario_id=usuario.id, app_id=app_id).first()
    if ja_comprado:
        return {"mensagem": "App já comprado"}

    compra = CompraApp(
        usuario_id=usuario.id,
        app_id=app_id,
        preco_pago=app.preco,
        data_compra=datetime.utcnow()
    )
    db.add(compra)
    db.commit()
    return {"mensagem": "Compra registrada com sucesso"}


# ---------- MEUS APLICATIVOS (ids) ----------
@router.get("/meus/ids")
def meus_apps_ids(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    apps = db.query(CompraApp).filter_by(usuario_id=usuario.id).all()
    return [c.app_id for c in apps]


# ---------- CRIAÇÃO VIA PAINEL ADMIN ----------
@router.post("/admin/adicionar_app")
def adicionar_aplicativo(app: AplicativoCreate, db: Session = Depends(get_db)):
    novo_app = Aplicativo(
        titulo=app.titulo,
        descricao=app.descricao,
        icone_url=app.icone_url,
        categoria=app.categoria,
        gratuito=app.gratuito,
        preco=0 if app.gratuito else app.preco,
        destaque=app.destaque,
        ativo=app.ativo
    )
    db.add(novo_app)
    db.commit()
    db.refresh(novo_app)
    return {"mensagem": "Aplicativo criado com sucesso", "id": novo_app.id}



@router.put("/{app_id}")
def atualizar_app(app_id: int, dados: dict, db: Session = Depends(get_db)):
    app = db.query(Aplicativo).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Aplicativo não encontrado")
    for key, value in dados.items():
        setattr(app, key, value)
    db.commit()
    return {"detail": "Aplicativo atualizado com sucesso"}

@router.delete("/{app_id}")
def deletar_app(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Aplicativo).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Aplicativo não encontrado")
    db.delete(app)
    db.commit()
    return {"detail": "Aplicativo deletado com sucesso"}



