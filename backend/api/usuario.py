from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario
from api.auth import get_usuario_logado
from models import Usuario, Diagnostico



router = APIRouter(prefix="/usuario", tags=["Usuário"])

@router.put("/nota_saude")
def salvar_diagnostico(
    dados: dict,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    # Reatacha o usuário na sessão atual para evitar erro de sessão
    usuario = db.merge(usuario)

    nota = dados.get("nota")
    respostas = dados.get("respostas")
    if nota is not None:
        usuario.nota_saude = f"{nota:.2f}%"
    if respostas is not None:
        usuario.respostas_saude = respostas

    db.commit()
    db.refresh(usuario)

    return {"mensagem": "Diagnóstico salvo com sucesso"}

# Novo endpoint para listar histórico de diagnósticos
@router.get("/diagnosticos")
def listar_diagnosticos(
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    diagnosticos = db.query(Diagnostico).filter(Diagnostico.usuario_id == usuario.id).order_by(Diagnostico.data_avaliacao.desc()).all()
    return [{
        "id": d.id,
        "data_avaliacao": d.data_avaliacao.isoformat() if d.data_avaliacao else None,
        "nota_geral": d.nota_geral,
        "respostas": d.respostas
    } for d in diagnosticos]




