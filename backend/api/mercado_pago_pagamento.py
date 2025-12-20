# backend/api/mercado_pago_pagamento.py

from __future__ import annotations

import os
import hmac
import hashlib
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

# Opcional (recomendado) para validar webhooks:
# Configure no painel do MP e coloque aqui também:
MERCADO_PAGO_WEBHOOK_SECRET = (os.getenv("MERCADO_PAGO_WEBHOOK_SECRET") or "").strip()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _parse_external_reference(external_reference: str) -> dict:
    """
    Padrão recomendado:
      kind=plano|plano_id=1|periodo=mensal|user_id=10|pag_id=55
      kind=curso|curso_id=9|user_id=10|pag_id=88

    Retorna dict com keys:
      kind, plano_id, curso_id, periodo, user_id, pag_id, etc.
    """
    ref: Dict[str, Any] = {}
    if not external_reference:
        return ref

    parts = [p.strip() for p in external_reference.split("|") if p.strip()]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            ref[k.strip()] = v.strip()

    # normaliza ints quando der
    for k in ("plano_id", "curso_id", "user_id", "pag_id"):
        if k in ref:
            try:
                ref[k] = int(ref[k])
            except Exception:
                pass

    return ref


def _extract_payment_id_from_request(request: Request, body_json: Optional[dict]) -> Optional[str]:
    """
    MP pode enviar:
      - JSON: {"type":"payment","data":{"id":"123"}}
      - JSON: {"action":"payment.created","data":{"id":...}}
      - Querystring: ?data.id=123&type=payment
      - Querystring: ?id=123
    """
    payment_id = None

    if isinstance(body_json, dict):
        data = body_json.get("data")
        if isinstance(data, dict) and data.get("id"):
            payment_id = str(data["id"])
        if not payment_id and body_json.get("id"):
            payment_id = str(body_json["id"])

    if not payment_id:
        qs = dict(request.query_params)
        if qs.get("data.id"):
            payment_id = str(qs["data.id"])
        elif qs.get("id"):
            payment_id = str(qs["id"])

    return payment_id


def _verify_webhook_signature(request: Request, payment_id: str) -> bool:
    """
    Validação opcional por assinatura.
    MP envia headers: x-signature e x-request-id; a doc descreve "secret signature". :contentReference[oaicite:3]{index=3}
    Se não tiver secret configurado, retorna True (não bloqueia).
    """
    if not MERCADO_PAGO_WEBHOOK_SECRET:
        return True

    x_signature = request.headers.get("x-signature") or ""
    x_request_id = request.headers.get("x-request-id") or ""
    if not x_signature or not x_request_id:
        return False

    # x-signature vem como: "ts=...,v1=..."
    parts = {}
    for part in x_signature.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()

    ts = parts.get("ts")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False

    manifest = f"id:{payment_id};request-id:{x_request_id};ts:{ts};"
    digest = hmac.new(
        MERCADO_PAGO_WEBHOOK_SECRET.encode("utf-8"),
        msg=manifest.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(digest, v1)


async def _mp_get_payment(payment_id: str) -> dict:
    """
    Consulta pagamento no MP: GET /v1/payments/{id}. :contentReference[oaicite:4]{index=4}
    """
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no ambiente.")

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)

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
        pass


# ---------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------
@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook de pagamentos (criação/atualização).
    Recomendação: habilitar evento de Payments (creation/update) no painel. :contentReference[oaicite:5]{index=5}

    Fluxo:
      1) extrai payment_id
      2) (opcional) valida assinatura
      3) consulta pagamento no MP
      4) localiza Pagamento no banco
      5) atualiza status e libera acesso se approved
    """
    # body pode não ser JSON -> não quebrar
    body_json = None
    try:
        body_json = await request.json()
    except Exception:
        body_json = None

    payment_id = _extract_payment_id_from_request(request, body_json)
    if not payment_id:
        return {"ok": True, "ignored": "sem_payment_id"}

    # validação opcional
    if MERCADO_PAGO_WEBHOOK_SECRET:
        if not _verify_webhook_signature(request, payment_id):
            raise HTTPException(status_code=401, detail="Webhook signature inválida.")

    try:
        mp = await _mp_get_payment(payment_id)  # se você estiver com versão async
    except Exception as e:
        # simulador do MP usa id fake; não derrubar webhook
        return {"ok": True, "warning": "mp_get_failed", "payment_id": payment_id}

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    preference_id = mp.get("preference_id") or None  # comum em preferências
    # alguns cenários trazem "order" / "merchant_order", mas não é sempre

    ref = _parse_external_reference(external_reference)

    # tenta localizar pagamento
    pagamento = None

    # 1) por pag_id (preferencial)
    pag_id = ref.get("pag_id")
    if isinstance(pag_id, int):
        pagamento = db.query(Pagamento).filter(Pagamento.id == pag_id).first()

    # 2) fallback: por mp_payment_id (se existir no model)
    if not pagamento:
        if hasattr(Pagamento, "mp_payment_id"):
            pagamento = db.query(Pagamento).filter(Pagamento.mp_payment_id == str(payment_id)).first()

    # 3) fallback: por external_reference (se existir campo no model)
    if not pagamento and external_reference:
        if hasattr(Pagamento, "mp_external_reference"):
            pagamento = db.query(Pagamento).filter(Pagamento.mp_external_reference == external_reference).first()

    if not pagamento:
        # não quebra webhook; só devolve info para debug
        return {
            "ok": True,
            "warning": "pagamento_nao_encontrado_no_banco",
            "payment_id": payment_id,
            "status": status,
            "external_reference": external_reference,
        }

    # Atualiza campos MP se existirem
    if hasattr(pagamento, "mp_payment_id"):
        pagamento.mp_payment_id = str(payment_id)
    if hasattr(pagamento, "mp_status"):
        pagamento.mp_status = status
    if hasattr(pagamento, "mp_external_reference"):
        pagamento.mp_external_reference = external_reference
    if hasattr(pagamento, "mp_preference_id"):
        pagamento.mp_preference_id = str(preference_id) if preference_id else None

    # Se ainda não aprovado, só salva status
    if status != "approved":
        pagamento.status = status  # pending, rejected, cancelled...
        db.commit()
        return {"ok": True, "status": status, "pagamento_id": pagamento.id}

    # -------------------------
    # APPROVED
    # -------------------------
    pagamento.status = "aprovado"
    db.commit()
    db.refresh(pagamento)

    usuario = db.query(Usuario).filter(Usuario.id == pagamento.usuario_id).first()
    if not usuario:
        return {"ok": True, "warning": "usuario_nao_encontrado", "pagamento_id": pagamento.id}

    kind = (ref.get("kind") or "").lower()

    # ---- PLANO
    if kind == "plano":
        periodo = (ref.get("periodo") or "mensal").lower()
        plano_id = ref.get("plano_id")

        plano_nome = getattr(pagamento, "plano", None) or "Plano"

        if isinstance(plano_id, int):
            p = db.query(Plano).filter(Plano.id == plano_id).first()
            if p and p.nome:
                plano_nome = p.nome

        usuario.plano_atual = plano_nome

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

    # ---- CURSO (se você quiser liberar aqui também)
    if kind == "curso":
        # Aqui depende do seu model de compras/inscrições.
        # Eu deixo o retorno claro para você plugar no seu modelo depois.
        return {
            "ok": True,
            "liberado": "curso",
            "usuario_id": usuario.id,
            "pagamento_id": pagamento.id,
            "external_reference": external_reference,
            "observacao": "Implementar aqui a liberação do curso conforme seu modelo (ex: tabela curso_compras).",
        }

    return {
        "ok": True,
        "status": "approved_sem_kind",
        "pagamento_id": pagamento.id,
        "external_reference": external_reference,
    }


@router.get("/__ping")
def ping():
    return {"ok": True}
