# backend/api/mercado_pago_pagamento.py

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Pagamento, Usuario
from backend.models.planos import Plano
from backend.utils.email_utils import enviar_email

router = APIRouter(prefix="/mercado_pago", tags=["Mercado Pago"])

MERCADO_PAGO_ACCESS_TOKEN = (os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or "").strip()


def _parse_external_reference(external_reference: str) -> dict:
    """
    Aceita padrão do checkout:
      kind=plano|plano_id=1|periodo=mensal|user_id=10|pag_id=55

    Retorna dict com keys: kind, plano_id, periodo, user_id, pag_id
    """
    ref = {}
    if not external_reference:
        return ref

    parts = [p.strip() for p in external_reference.split("|") if p.strip()]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            ref[k.strip()] = v.strip()

    # normaliza ints quando der
    for k in ("plano_id", "user_id", "pag_id"):
        if k in ref:
            try:
                ref[k] = int(ref[k])
            except Exception:
                pass

    return ref


def _mp_get_payment(payment_id: str) -> dict:
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no ambiente.")
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}
    r = httpx.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar pagamento no MP: {r.text}")
    return r.json() or {}


def _email_plano_aprovado(usuario: Usuario, plano_nome: str, periodo: str):
    try:
        enviar_email(
            para=usuario.email,
            assunto="Plano ativado no MivMark",
            html=f"""
            <h3>Pagamento aprovado</h3>
            <p>Olá, {usuario.nome or ""}.</p>
            <p>Seu plano <b>{plano_nome}</b> foi ativado com sucesso ({periodo}).</p>
            <p>Você já pode fazer login no sistema normalmente.</p>
            """,
        )
    except Exception:
        # não quebra webhook por falha de e-mail
        pass


@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook MP: recebe notificações (payment).
    Ao approved:
      - atualiza Pagamento
      - ativa plano no usuário
    """
    data = await request.json()

    # MP envia de vários formatos: tenta extrair payment_id
    payment_id = None

    # formato comum:
    # {"type":"payment","data":{"id":"123"}}
    if isinstance(data, dict):
        if isinstance(data.get("data"), dict) and data["data"].get("id"):
            payment_id = str(data["data"]["id"])

        # alguns casos:
        # {"action":"payment.created","data":{"id":...}}
        if not payment_id and isinstance(data.get("id"), (str, int)):
            payment_id = str(data["id"])

    # também pode vir por querystring (raramente); tenta pegar do request
    if not payment_id:
        qs = dict(request.query_params)
        if "data.id" in qs:
            payment_id = qs["data.id"]
        elif "id" in qs:
            payment_id = qs["id"]

    if not payment_id:
        return {"ok": True, "ignored": "sem_payment_id"}

    mp = _mp_get_payment(payment_id)

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    preference_id = mp.get("order", {}).get("id") or mp.get("preference_id") or None

    ref = _parse_external_reference(external_reference)

    # ✅ tentamos localizar pagamento pelo pag_id
    pagamento = None
    pag_id = ref.get("pag_id")
    if isinstance(pag_id, int):
        pagamento = db.query(Pagamento).filter(Pagamento.id == pag_id).first()

    # fallback: por mp_payment_id se você tiver esse campo no model
    if not pagamento:
        try:
            pagamento = db.query(Pagamento).filter(Pagamento.mp_payment_id == str(payment_id)).first()
        except Exception:
            pagamento = None

    # Se ainda não achou, não quebra. Só registra retorno.
    if not pagamento:
        return {
            "ok": True,
            "warning": "pagamento_nao_encontrado",
            "payment_id": payment_id,
            "status": status,
            "external_reference": external_reference,
        }

    # Atualiza campos MP se existirem no model
    try:
        pagamento.mp_payment_id = str(payment_id)
    except Exception:
        pass

    try:
        pagamento.mp_status = status
    except Exception:
        pass

    try:
        pagamento.mp_external_reference = external_reference
    except Exception:
        pass

    try:
        pagamento.mp_preference_id = str(preference_id) if preference_id else None
    except Exception:
        pass

    # Se não aprovado, só salva status
    if status != "approved":
        pagamento.status = status  # pendente, rejected, etc
        db.commit()
        return {"ok": True, "status": status, "pagamento_id": pagamento.id}

    # ✅ aprovado: ativa plano
    pagamento.status = "aprovado"
    db.commit()
    db.refresh(pagamento)

    usuario = db.query(Usuario).filter(Usuario.id == pagamento.usuario_id).first()
    if not usuario:
        return {"ok": True, "warning": "usuario_nao_encontrado", "pagamento_id": pagamento.id}

    # descobre plano/periodo
    kind = (ref.get("kind") or "").lower()
    periodo = (ref.get("periodo") or "mensal").lower()

    if kind == "plano":
        plano_id = ref.get("plano_id")
        plano_nome = pagamento.plano

        if isinstance(plano_id, int):
            p = db.query(Plano).filter(Plano.id == plano_id).first()
            if p and p.nome:
                plano_nome = p.nome

        # ativa no usuário
        usuario.plano_atual = plano_nome

        # se você tiver campo de expiração (opcional), tenta setar
        expira = datetime.utcnow() + (timedelta(days=365) if periodo == "anual" else timedelta(days=30))
        for campo in ("plano_expira_em", "plano_expira", "expira_em"):
            if hasattr(usuario, campo):
                setattr(usuario, campo, expira)
                break

        db.commit()

        _email_plano_aprovado(usuario, plano_nome, periodo)

        return {
            "ok": True,
            "liberado": "plano",
            "usuario_id": usuario.id,
            "plano": plano_nome,
            "periodo": periodo,
            "pagamento_id": pagamento.id,
        }

    # se vier outra coisa no futuro (curso, etc)
    return {
        "ok": True,
        "status": "approved_sem_kind",
        "pagamento_id": pagamento.id,
        "external_reference": external_reference,
    }


@router.get("/__ping")
def ping():
    return {"ok": True}
