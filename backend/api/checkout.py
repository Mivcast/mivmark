# backend/api/checkout.py

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Usuario, Pagamento
from backend.models.planos import Plano
from backend.models.cupom import CupomDesconto

# ✅ você confirmou que existe em backend/api/usuario.py
from backend.api.usuario import hash_senha


router = APIRouter(prefix="/checkout", tags=["Checkout Público"])

MERCADO_PAGO_ACCESS_TOKEN = (os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or "").strip()
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "").strip().rstrip("/")
BACKEND_URL = (os.getenv("BACKEND_URL") or "").strip().rstrip("/")


def _mp_notification_url() -> Optional[str]:
    if not BACKEND_URL:
        return None
    # seu webhook real está em /mercado_pago/webhook
    return f"{BACKEND_URL}/mercado_pago/webhook"


def _normalizar_codigo(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    c = (c or "").strip().lower()
    return c or None


def _cupom_valido_para_plano(cupom: CupomDesconto, plano: Plano) -> bool:
    alvo = (cupom.plano_nome or "").strip().lower()
    if not alvo or alvo == "todos":
        return True
    return alvo == (plano.nome or "").strip().lower()


def criar_preferencia_mp(titulo: str, valor: float, external_reference: str) -> dict:
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no ambiente.")

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    body = {
        "items": [{
            "title": titulo,
            "quantity": 1,
            "unit_price": float(valor),
        }],
        "external_reference": external_reference,
    }

    if FRONTEND_URL:
        body["back_urls"] = {
            "success": f"{FRONTEND_URL}/",
            "failure": f"{FRONTEND_URL}/",
            "pending": f"{FRONTEND_URL}/",
        }
        body["auto_return"] = "approved"

    nurl = _mp_notification_url()
    if nurl:
        body["notification_url"] = nurl

    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    if resp.status_code != 201:
        raise HTTPException(status_code=500, detail=f"Erro ao criar preferência Mercado Pago: {resp.text}")

    data = resp.json() or {}
    return {"preference_id": data.get("id"), "init_point": data.get("init_point")}


class CheckoutPlanoIn(BaseModel):
    plano_id: int
    nome: str
    email: EmailStr
    senha: str
    periodo: Literal["mensal", "anual"] = "mensal"
    cupom: Optional[str] = None


@router.post("/plano")
def checkout_plano(payload: CheckoutPlanoIn, db: Session = Depends(get_db)):
    # 1) Busca plano
    plano = db.query(Plano).filter(Plano.id == int(payload.plano_id)).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    valor_base = float(plano.preco_anual or 0.0) if payload.periodo == "anual" else float(plano.preco_mensal or 0.0)
    if valor_base <= 0:
        raise HTTPException(status_code=400, detail="Plano com preço inválido (0).")

    # 2) Cria (ou detecta) usuário
    email_norm = (payload.email or "").strip().lower()

    usuario = db.query(Usuario).filter(func.lower(func.trim(Usuario.email)) == email_norm).first()
    if usuario:
        # Para evitar fraude/duplicidade: se já existe, força login antes de comprar.
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado. Faça login para assinar/alterar plano.")

    usuario = Usuario(
        nome=(payload.nome or "").strip(),
        email=email_norm,
        senha_hash=hash_senha(payload.senha),
        plano_atual="Gratuito",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    # 3) Cupom (escopo=plano)
    valor_final = valor_base
    codigo = _normalizar_codigo(payload.cupom)
    if codigo:
        cupom = (
            db.query(CupomDesconto)
            .filter(
                func.lower(func.trim(CupomDesconto.codigo)) == codigo,
                CupomDesconto.ativo.is_(True),
                func.lower(func.trim(CupomDesconto.escopo)) == "plano",
            )
            .first()
        )
        if not cupom:
            raise HTTPException(status_code=400, detail="Cupom inválido.")
        if not _cupom_valido_para_plano(cupom, plano):
            raise HTTPException(status_code=400, detail="Cupom não válido para este plano.")
        desconto = float(cupom.desconto_percent or 0.0)
        if desconto <= 0 or desconto > 100:
            raise HTTPException(status_code=400, detail="Cupom com desconto inválido.")
        valor_final = valor_final * (1 - desconto / 100.0)

    # 4) Pagamento pendente
    pagamento = Pagamento(
        usuario_id=usuario.id,
        plano=plano.nome,
        valor=float(valor_final),
        status="pendente",
        gateway="mercado_pago",
        data_pagamento=datetime.utcnow(),
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    # 5) Preferência MP + external_reference para o webhook achar tudo
    external_reference = f"kind=plano|plano_id={plano.id}|periodo={payload.periodo}|user_id={usuario.id}|pag_id={pagamento.id}"
    pref = criar_preferencia_mp(
        titulo=f"Plano {plano.nome} ({payload.periodo})",
        valor=float(valor_final),
        external_reference=external_reference,
    )

    init_point = pref.get("init_point")
    if not init_point:
        raise HTTPException(status_code=500, detail="Preferência criada sem init_point.")

    return {
        "ok": True,
        "usuario_id": usuario.id,
        "pagamento_id": pagamento.id,
        "plano": plano.nome,
        "periodo": payload.periodo,
        "valor": float(valor_final),
        "init_point": init_point,
        "preference_id": pref.get("preference_id"),
    }
