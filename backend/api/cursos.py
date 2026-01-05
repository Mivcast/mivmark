# backend/api/cursos.py

from __future__ import annotations

import os
from datetime import datetime, date
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_usuario_logado
from backend.models import Usuario
from backend.models.curso import Curso, Aula, CompraCurso, ProgressoCurso, PagamentoCurso
from backend.models.cupom import CupomDesconto
from backend.models.planos import Plano  # (não é usado aqui, mas deixo se você for reaproveitar lógica)


router = APIRouter(prefix="/cursos", tags=["Cursos"])


# =========================================================
# Mercado Pago (Checkout real)
# =========================================================
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/")  # ex: https://seu-frontend.onrender.com
BACKEND_URL = os.getenv("BACKEND_URL", "").strip().rstrip("/")    # ex: https://seu-backend.onrender.com


def _mp_notification_url() -> Optional[str]:
    if not BACKEND_URL:
        return None
    # ajuste quando você tiver o webhook definitivo de cursos
    # exemplo: /mercado-pago/webhook (ou /mercado_pago/webhook)
    return f"{BACKEND_URL}/api/mercado-pago/webhook"


def criar_preferencia_mp(titulo: str, valor: float, referencia_externa: str) -> dict:
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no ambiente.")

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    back_urls = None
    if FRONTEND_URL:
        back_urls = {
            "success": f"{FRONTEND_URL}/",
            "failure": f"{FRONTEND_URL}/",
            "pending": f"{FRONTEND_URL}/",
        }

    body = {
        "items": [{
            "title": titulo,
            "quantity": 1,
            "unit_price": float(valor),
        }],
        "external_reference": referencia_externa,
    }

    if back_urls:
        body["back_urls"] = back_urls
        body["auto_return"] = "approved"

    nurl = _mp_notification_url()
    if nurl:
        body["notification_url"] = nurl

    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    if resp.status_code != 201:
        raise HTTPException(status_code=500, detail=f"Erro ao criar preferência Mercado Pago: {resp.text}")

    data = resp.json()
    return {
        "preference_id": data.get("id"),
        "init_point": data.get("init_point"),
    }


# =========================================================
# Schemas
# =========================================================
class AulaSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    video_url: Optional[str] = None
    ordem: Optional[int] = None

    class Config:
        from_attributes = True


class AulaCreate(BaseModel):
    curso_id: int
    titulo: str
    descricao: Optional[str] = None
    video_url: Optional[str] = None
    ordem: Optional[int] = None


class AulaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    video_url: Optional[str] = None
    ordem: Optional[int] = None

    class Config:
        from_attributes = True


class CursoSchema(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    capa_url: Optional[str] = None
    categoria: Optional[str] = None
    gratuito: bool
    preco: Optional[float] = None
    destaque: bool
    ativo: bool = True
    ordem: Optional[int] = None
    aulas: List[AulaSchema] = []

    class Config:
        from_attributes = True


class CursoCreate(BaseModel):
    titulo: str
    descricao: str
    capa_url: Optional[str] = None
    categoria: Optional[str] = None
    gratuito: bool = True
    preco: Optional[float] = None
    destaque: bool = False
    ativo: bool = True
    ordem: Optional[int] = None


class CursoUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    capa_url: Optional[str] = None
    categoria: Optional[str] = None
    gratuito: Optional[bool] = None
    preco: Optional[float] = None
    destaque: Optional[bool] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None


class ComprarCursoResponse(BaseModel):
    mensagem: str
    pagamento_id: Optional[int] = None
    valor: Optional[float] = None
    status: Optional[str] = None
    init_point: Optional[str] = None
    preference_id: Optional[str] = None


# =========================================================
# Helpers
# =========================================================
def _so_admin(usuario: Usuario):
    if getattr(usuario, "is_admin", False) is True:
        return
    if getattr(usuario, "tipo_usuario", "") == "admin":
        return
    raise HTTPException(status_code=403, detail="Acesso negado. Apenas admin.")


def _cupom_expirado(valido_ate) -> bool:
    """
    CupomDesconto.valido_ate pode estar como date ou datetime dependendo do seu model/banco.
    Aqui tratamos ambos com segurança.
    """
    if not valido_ate:
        return False
    if isinstance(valido_ate, datetime):
        return valido_ate.date() < date.today()
    if isinstance(valido_ate, date):
        return valido_ate < date.today()
    return False


# =========================================================
# Rotas públicas
# =========================================================
@router.get("/progresso")
def progresso_usuario(
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    progresso = db.query(ProgressoCurso).filter_by(usuario_id=usuario.id).all()
    ids_concluidos = [p.aula_id for p in progresso]
    return {"aulas_concluidas": ids_concluidos}


@router.get("/", response_model=List[CursoSchema])
def listar_cursos(db: Session = Depends(get_db)):
    return (
        db.query(Curso)
        .filter(Curso.ativo == True)
        .order_by(func.coalesce(Curso.ordem, 999999), Curso.id.asc())
        .all()
    )


def usuario_tem_acesso_ao_curso(db: Session, usuario_id: int, curso: Curso) -> bool:
    if curso.gratuito:
        return True
    ja = db.query(CompraCurso).filter_by(usuario_id=usuario_id, curso_id=curso.id).first()
    return ja is not None

@router.get("/{curso_id}", response_model=CursoSchema)
def detalhes_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    curso = db.query(Curso).filter(Curso.id == curso_id, Curso.ativo == True).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    if not usuario_tem_acesso_ao_curso(db, usuario.id, curso):
        raise HTTPException(status_code=403, detail="Curso não liberado. Pagamento não identificado.")

    return curso



@router.get("/{curso_id}/preview", response_model=CursoSchema)
def detalhes_curso_preview(
    curso_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    curso = db.query(Curso).filter(Curso.id == curso_id, Curso.ativo == True).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    # Converte para schema e remove video_url de TODAS as aulas (apenas vitrine)
    data = CursoSchema.from_orm(curso).model_dump()  # pydantic v2
    # se estiver em pydantic v1: data = CursoSchema.from_orm(curso).dict()

    aulas = data.get("aulas") or []
    for a in aulas:
        a["video_url"] = None  # nunca manda vídeo no preview

    data["aulas"] = aulas
    return data



# =========================================================
# Compra e progresso
# =========================================================
@router.post("/{curso_id}/comprar", response_model=ComprarCursoResponse)
def comprar_curso(
    curso_id: int,
    cupom: Optional[str] = Query(default=None),
    metodo: str = Query(default="pix"),
    gateway: str = Query(default="mercado_pago"),
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    curso = db.query(Curso).filter(Curso.id == curso_id, Curso.ativo == True).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso inválido.")

    # Já comprado ou gratuito?
    ja_tem = db.query(CompraCurso).filter_by(usuario_id=usuario.id, curso_id=curso_id).first()
    if ja_tem or curso.gratuito:
        return ComprarCursoResponse(mensagem="Curso já liberado.")

    valor = float(curso.preco or 0.0)

    # ✅ Cupom escopo=curso
    codigo_cupom = None
    if cupom:
        codigo_cupom = (cupom or "").strip().lower()
        c = (
            db.query(CupomDesconto)
            .filter(
                func.lower(CupomDesconto.codigo) == codigo_cupom,
                CupomDesconto.ativo == True,
                CupomDesconto.escopo == "curso",
            )
            .first()
        )
        if not c:
            raise HTTPException(status_code=400, detail="Cupom inválido.")

        if _cupom_expirado(c.valido_ate):
            raise HTTPException(status_code=400, detail="Cupom expirado.")

        if c.curso_id and int(c.curso_id) != int(curso.id):
            raise HTTPException(status_code=400, detail="Cupom não válido para este curso.")

        desconto = float(c.desconto_percent or 0.0)
        if desconto <= 0 or desconto > 100:
            raise HTTPException(status_code=400, detail="Cupom com desconto inválido.")

        valor = valor * (1 - desconto / 100.0)

    # Se valor final for 0, libera na hora
    if valor <= 0.01:
        compra = CompraCurso(usuario_id=usuario.id, curso_id=curso.id, preco_pago=0.0)
        db.add(compra)
        db.commit()
        return ComprarCursoResponse(mensagem="Curso liberado com cupom de 100%.")

    # Registra pagamento pendente (interno)
    pagamento = PagamentoCurso(
        usuario_id=usuario.id,
        curso_id=curso.id,
        status="pendente",
        valor=float(valor),
        metodo=metodo,
        gateway=gateway,
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    # ✅ Mercado Pago real: cria preferência
    referencia = f"curso:{curso.id}|user:{usuario.id}|pag:{pagamento.id}|ts:{int(datetime.utcnow().timestamp())}"
    pref = criar_preferencia_mp(
        titulo=f"Curso: {curso.titulo}",
        valor=float(valor),
        referencia_externa=referencia,
    )

    return ComprarCursoResponse(
        mensagem="Link de pagamento gerado",
        pagamento_id=pagamento.id,
        valor=float(valor),
        status="aguardando",
        init_point=pref.get("init_point"),
        preference_id=pref.get("preference_id"),
    )


@router.post("/aula/{aula_id}/concluir")
def concluir_aula(
    aula_id: int,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    existe = db.query(ProgressoCurso).filter_by(usuario_id=usuario.id, aula_id=aula_id).first()
    if existe:
        return {"mensagem": "Aula já estava marcada como concluída"}

    registro = ProgressoCurso(usuario_id=usuario.id, aula_id=aula_id)
    db.add(registro)
    db.commit()
    return {"mensagem": "Aula marcada como concluída"}


# =========================================================
# Área administrativa
# =========================================================
@router.post("/admin/curso")
def criar_curso(
    curso: CursoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    ordem = curso.ordem
    if ordem is None:
        ultimo = db.query(Curso).order_by(Curso.ordem.desc().nullslast(), Curso.id.desc()).first()
        ordem = (ultimo.ordem + 1) if ultimo and ultimo.ordem is not None else 1

    novo = Curso(
        titulo=curso.titulo,
        descricao=curso.descricao,
        capa_url=curso.capa_url,
        categoria=curso.categoria,
        gratuito=curso.gratuito,
        preco=curso.preco,
        destaque=curso.destaque,
        ativo=curso.ativo,
        criado_em=datetime.utcnow(),
        ordem=ordem,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "mensagem": "Curso criado com sucesso!"}


@router.put("/admin/curso/{curso_id}")
def atualizar_curso_admin(
    curso_id: int,
    dados: CursoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    curso = db.query(Curso).filter_by(id=curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    campos = dados.dict(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(curso, campo, valor)

    db.commit()
    db.refresh(curso)
    return {"mensagem": "Curso atualizado com sucesso!", "id": curso.id}

@router.get("/admin/cursos", response_model=List[CursoSchema])
def listar_cursos_admin(
    incluir_inativos: bool = Query(default=True),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    q = db.query(Curso)

    # Se quiser ver só ativos no admin, passe incluir_inativos=false
    if not incluir_inativos:
        q = q.filter(Curso.ativo == True)

    return (
        q.order_by(func.coalesce(Curso.ordem, 999999), Curso.id.asc())
        .all()
    )


@router.post("/admin/aula")
def criar_aula(
    aula: AulaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    ordem = aula.ordem
    if ordem is None:
        ultimo = (
            db.query(Aula)
            .filter(Aula.curso_id == aula.curso_id)
            .order_by(Aula.ordem.desc().nullslast(), Aula.id.desc())
            .first()
        )
        ordem = (ultimo.ordem + 1) if ultimo and ultimo.ordem is not None else 1

    nova = Aula(
        curso_id=aula.curso_id,
        titulo=aula.titulo,
        descricao=aula.descricao,
        video_url=aula.video_url,
        ordem=ordem,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {"mensagem": "Aula criada com sucesso", "id": nova.id}


@router.put("/admin/aula/{aula_id}")
def atualizar_aula(
    aula_id: int,
    dados: AulaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    aula = db.query(Aula).filter_by(id=aula_id).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula não encontrada.")

    campos = dados.dict(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(aula, campo, valor)

    db.commit()
    db.refresh(aula)
    return {"mensagem": "Aula atualizada com sucesso", "id": aula.id}


# =========================================================
# DEV: confirmar pagamento manualmente (mantido)
# =========================================================
@router.post("/pagamentos/{pagamento_id}/confirmar")
def confirmar_pagamento_dev(
    pagamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    if getattr(usuario, "tipo_usuario", "") != "admin" and getattr(usuario, "is_admin", False) is not True:
        raise HTTPException(status_code=403, detail="Apenas admin pode confirmar pagamento (DEV).")

    pag = db.query(PagamentoCurso).filter(PagamentoCurso.id == pagamento_id).first()
    if not pag:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado.")

    if pag.status == "pago":
        return {"ok": True, "mensagem": "Pagamento já estava confirmado."}

    pag.status = "pago"
    if hasattr(pag, "pago_em"):
        pag.pago_em = datetime.utcnow()

    ja = db.query(CompraCurso).filter_by(usuario_id=pag.usuario_id, curso_id=pag.curso_id).first()
    if not ja:
        compra = CompraCurso(
            usuario_id=pag.usuario_id,
            curso_id=pag.curso_id,
            preco_pago=float(pag.valor or 0.0),
        )
        db.add(compra)

    db.commit()
    return {"ok": True, "mensagem": "Pagamento confirmado e curso liberado."}



MP_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "").strip()
MP_WEBHOOK_URL = os.getenv("MERCADO_PAGO_WEBHOOK_URL", "").strip()

@router.post("/{curso_id}/comprar_mp")
def comprar_curso_mercado_pago(
    curso_id: int,
    cupom: Optional[str] = Query(default=None),
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado.")
    if not MP_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_WEBHOOK_URL não configurado.")

    curso = db.query(Curso).filter(Curso.id == curso_id, Curso.ativo == True).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso inválido.")

    if curso.gratuito:
        # libera direto
        ja = db.query(CompraCurso).filter_by(usuario_id=usuario.id, curso_id=curso.id).first()
        if not ja:
            db.add(CompraCurso(usuario_id=usuario.id, curso_id=curso.id, preco_pago=0.0))
            db.commit()
        return {"liberado": True, "mensagem": "Curso gratuito liberado."}

    # já comprado?
    ja_tem = db.query(CompraCurso).filter_by(usuario_id=usuario.id, curso_id=curso.id).first()
    if ja_tem:
        return {"liberado": True, "mensagem": "Curso já liberado."}

    valor = float(curso.preco or 0.0)

    # aplica cupom real (escopo=curso)
    cupom_norm = None
    if cupom:
        cupom_norm = cupom.strip().lower()
        c = (
            db.query(CupomDesconto)
            .filter(
                func.lower(CupomDesconto.codigo) == cupom_norm,
                CupomDesconto.ativo == True,
                CupomDesconto.escopo == "curso",
            )
            .first()
        )
        if not c:
            raise HTTPException(status_code=400, detail="Cupom inválido.")
        if c.valido_ate and c.valido_ate < date.today():
            raise HTTPException(status_code=400, detail="Cupom expirado.")
        if c.curso_id and c.curso_id != curso.id:
            raise HTTPException(status_code=400, detail="Cupom não válido para este curso.")

        desconto = float(c.desconto_percent or 0)
        if desconto < 0 or desconto > 100:
            raise HTTPException(status_code=400, detail="Cupom com desconto inválido.")
        valor = valor * (1 - desconto / 100.0)

    valor = round(max(valor, 0.0), 2)

    # se ficou grátis
    if valor <= 0.01:
        db.add(CompraCurso(usuario_id=usuario.id, curso_id=curso.id, preco_pago=0.0))
        db.commit()
        return {"liberado": True, "mensagem": "Curso liberado com cupom 100%."}

    # cria preferência MP
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json"}

    body = {
        "items": [{
            "title": f"Curso: {curso.titulo}",
            "quantity": 1,
            "unit_price": float(valor),
            "currency_id": "BRL",
        }],
        "payment_methods": {
            "excluded_payment_methods": [],
            "excluded_payment_types": [],
            "installments": 12
        },
        "notification_url": MP_WEBHOOK_URL,
        "metadata": {
            "tipo": "curso",
            "curso_id": int(curso.id),
            "usuario_id": int(usuario.id),
            "cupom": cupom_norm,
            "valor_final": float(valor),
        }
    }

    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    if resp.status_code != 201:
        raise HTTPException(status_code=500, detail=f"Erro ao criar preferência MP: {resp.text}")

    data = resp.json()
    return {"init_point": data.get("init_point"), "preference_id": data.get("id"), "valor": float(valor)}

