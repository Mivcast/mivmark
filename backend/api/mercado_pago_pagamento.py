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
MERCADO_PAGO_WEBHOOK_SECRET = (os.getenv("MERCADO_PAGO_WEBHOOK_SECRET") or "").strip()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _parse_external_reference(external_reference: str) -> dict:
    ref: Dict[str, Any] = {}
    if not external_reference:
        return ref

    parts = [p.strip() for p in external_reference.split("|") if p.strip()]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            ref[k.strip()] = v.strip()

    for k in ("plano_id", "curso_id", "user_id", "pag_id"):
        if k in ref:
            try:
                ref[k] = int(ref[k])
            except Exception:
                pass

    return ref


def _extract_payment_id_from_request(request: Request, body_json: Optional[dict]) -> Optional[str]:
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
    Validação opcional. Se secret não estiver configurado, não bloqueia.
    """
    if not MERCADO_PAGO_WEBHOOK_SECRET:
        return True

    x_signature = request.headers.get("x-signature") or ""
    # alguns ambientes usam x-request-id, outros x-mp-request-id
    x_request_id = request.headers.get("x-request-id") or request.headers.get("x-mp-request-id") or ""
    if not x_signature or not x_request_id:
        return False

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
    Nunca derruba webhook. Se falhar, retorna {}.
    """
    if not MERCADO_PAGO_ACCESS_TOKEN:
        return {}

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers)
    except Exception:
        return {}

    if r.status_code != 200:
        return {}

    try:
        return r.json() or {}
    except Exception:
        return {}


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
# Endpoints
# ---------------------------------------------------------------------
@router.get("/webhook")
def mercado_pago_webhook_get():
    # alguns validadores/testes batem em GET
    return {"ok": True, "info": "webhook_up"}


@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
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

    mp = await _mp_get_payment(payment_id)

    # Se não conseguiu consultar o pagamento (simulador / id inválido / token faltando),
    # não derruba o webhook.
    if not mp:
        return {"ok": True, "ignored": "mp_nao_consultavel", "payment_id": payment_id}

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    preference_id = mp.get("preference_id") or None

    ref = _parse_external_reference(external_reference)

    pagamento = None

    # 1) por pag_id (preferencial)
    pag_id = ref.get("pag_id")
    if isinstance(pag_id, int):
        pagamento = db.query(Pagamento).filter(Pagamento.id == pag_id).first()

    # 2) fallback: por mp_payment_id
    if not pagamento and hasattr(Pagamento, "mp_payment_id"):
        pagamento = db.query(Pagamento).filter(Pagamento.mp_payment_id == str(payment_id)).first()

    # 3) fallback: por mp_external_reference
    if not pagamento and external_reference and hasattr(Pagamento, "mp_external_reference"):
        pagamento = db.query(Pagamento).filter(Pagamento.mp_external_reference == external_reference).first()

    if not pagamento:
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

    # Ainda não aprovado: salva status e sai
    if status != "approved":
        pagamento.status = status
        db.commit()
        return {"ok": True, "status": status, "pagamento_id": pagamento.id}

    # APPROVED
    pagamento.status = "aprovado"
    db.commit()
    db.refresh(pagamento)

    usuario = db.query(Usuario).filter(Usuario.id == pagamento.usuario_id).first()
    if not usuario:
        return {"ok": True, "warning": "usuario_nao_encontrado", "pagamento_id": pagamento.id}

    kind = (ref.get("kind") or "").lower()

    # PLANO
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

    # CURSO (placeholder)
    if kind == "curso":
        return {
            "ok": True,
            "liberado": "curso",
            "usuario_id": usuario.id,
            "pagamento_id": pagamento.id,
            "external_reference": external_reference,
            "observacao": "Implementar a liberação do curso conforme seu modelo.",
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
