# backend/api/checkout_publico.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Usuario, Pagamento
from backend.models.planos import Plano
from backend.api.usuario import hash_senha

router = APIRouter(prefix="/checkout_publico", tags=["Checkout Público"])

MP_ACCESS_TOKEN = (os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or "").strip()
BACKEND_PUBLIC_URL = (os.getenv("BACKEND_PUBLIC_URL") or "").strip().rstrip("/")  # ex: https://seu-backend.onrender.com


class CheckoutPlanoIn(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    plano_id: int
    periodo: str = "mensal"  # mensal | anual
    cupom: Optional[str] = None


def _mp_headers() -> Dict[str, str]:
    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado.")
    return {"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json"}


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _norm_codigo(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    c = (c or "").strip().lower()
    return c or None


async def _validar_cupom_plano(api_url_base: str, codigo: str, plano_nome: str) -> float:
    """
    Valida cupom no seu backend usando /cupons.
    Retorna desconto_percent (0..100). Se inválido, levanta HTTPException 400.
    Se você não quiser cupom no checkout público, basta remover esta função e o trecho de uso.
    """
    # Como este arquivo está no backend, não temos "API_URL" do streamlit.
    # Então vamos validar no próprio DB (melhor) — mas como você não mandou o model de cupom aqui,
    # vamos validar via endpoint /cupons (que já existe).
    #
    # Para isso, BACKEND_PUBLIC_URL precisa existir em produção; local pode ficar vazio e a validação cairá no erro.
    if not api_url_base:
        raise HTTPException(status_code=400, detail="Cupom não pode ser validado (BACKEND_PUBLIC_URL vazio).")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{api_url_base}/cupons", timeout=30)
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail="Falha ao validar cupom.")
        cupons = r.json() or []

    codigo = codigo.strip().lower()
    alvo_plano = (plano_nome or "").strip().lower()

    for c in cupons:
        cod = (c.get("codigo") or "").strip().lower()
        if cod != codigo:
            continue
        if not c.get("ativo", True):
            break
        escopo = (c.get("escopo") or "").strip().lower()
        if escopo and escopo != "plano":
            break
        # se tiver plano_nome no cupom, respeita
        plano_cupom = (c.get("plano_nome") or "").strip().lower()
        if plano_cupom and plano_cupom not in ("todos", alvo_plano):
            break

        desconto = float(c.get("desconto_percent") or 0.0)
        if desconto <= 0 or desconto > 100:
            break
        return desconto

    raise HTTPException(status_code=400, detail="Cupom inválido ou não aplicável ao plano.")


def _notification_url() -> Optional[str]:
    if not BACKEND_PUBLIC_URL:
        return None
    # No seu Swagger está /api/mercado_pago/webhook
    # mas seu router também pode existir como /mercado_pago/webhook dependendo de como você incluiu.
    # Vamos padronizar para o do Swagger e manter fallback no payload via "additional_info" não é possível,
    # então aqui usamos o mais provável e garantimos no main que está batendo.
    return f"{BACKEND_PUBLIC_URL}/api/mercado_pago/webhook"


@router.post("/plano")
async def checkout_plano_publico(payload: CheckoutPlanoIn, db: Session = Depends(get_db)):
    # 1) Plano
    plano = db.query(Plano).filter(Plano.id == int(payload.plano_id)).first()
    if not plano or not getattr(plano, "ativo", True):
        raise HTTPException(status_code=404, detail="Plano não encontrado ou inativo.")

    periodo = (payload.periodo or "mensal").strip().lower()
    if periodo not in ("mensal", "anual"):
        periodo = "mensal"

    valor_base = float(plano.preco_anual or 0.0) if periodo == "anual" else float(plano.preco_mensal or 0.0)
    if valor_base <= 0:
        raise HTTPException(status_code=400, detail="Plano com preço inválido (0).")

    # 2) Usuário (cria como pendente e SEM liberar plano pago)
    email_norm = _norm_email(str(payload.email))
    usuario = (
        db.query(Usuario)
        .filter(func.lower(func.trim(Usuario.email)) == email_norm)
        .first()
    )

    if usuario:
        # Regra correta:
        # - Se já existe e é ativo/cliente, obrigar login para trocar plano (anti-fraude)
        # - Se já existe e é pendente, reaproveita (não cria outro)
        tipo = (getattr(usuario, "tipo_usuario", "") or "").lower()
        if tipo not in ("pendente", "demo"):
            raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado. Faça login para assinar/alterar plano.")
    else:
        usuario = Usuario(
            nome=(payload.nome or "").strip(),
            email=email_norm,
            senha_hash=hash_senha(payload.senha),
            tipo_usuario="pendente",
            plano_atual="Gratuito",
            data_criacao=datetime.utcnow(),
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    # 3) Cupom
    valor_final = float(valor_base)
    codigo = _norm_codigo(payload.cupom)
    if codigo:
        # Se você quiser validar cupom direto no DB, eu adapto depois.
        # Por enquanto, valida via endpoint /cupons usando BACKEND_PUBLIC_URL.
        desconto = await _validar_cupom_plano(BACKEND_PUBLIC_URL, codigo, plano.nome)
        valor_final = valor_final * (1 - float(desconto) / 100.0)

    # 4) Pagamento (model atual: plano=str, valor, status, gateway, data_pagamento)
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

    # 5) external_reference no formato que o seu webhook já entende (plano:{id}|periodo:{x}|user:{id}|pag:{id})
    external_reference = (
        f"plano:{plano.id}|periodo:{periodo}|user:{usuario.id}|pag:{pagamento.id}|ts:{int(datetime.utcnow().timestamp())}"
    )

    # 6) Preferência MP
    pref_payload: Dict[str, Any] = {
        "items": [{
            "title": f"Plano {plano.nome} ({periodo})",
            "quantity": 1,
            "unit_price": float(valor_final),
        }],
        "payer": {"email": email_norm},
        "external_reference": external_reference,
    }

    nurl = _notification_url()
    if nurl:
        pref_payload["notification_url"] = nurl

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.mercadopago.com/checkout/preferences",
            headers=_mp_headers(),
            json=pref_payload,
        )

    if r.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Erro MP ({r.status_code}): {r.text}")

    data = r.json() or {}
    init_point = data.get("init_point")
    if not init_point:
        raise HTTPException(status_code=500, detail="Preferência criada sem init_point.")

    return {
        "ok": True,
        "init_point": init_point,
        "preference_id": data.get("id"),
        "usuario_id": usuario.id,
        "pagamento_id": pagamento.id,
        "external_reference": external_reference,
        "valor": float(valor_final),
        "periodo": periodo,
        "plano": plano.nome,
    }
