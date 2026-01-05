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
from backend.models.curso import Curso, CompraCurso
from backend.models.curso import PagamentoCurso

from backend.api.auth import get_usuario_logado 

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
        elif ":" in p:
            k, v = p.split(":", 1)
        else:
            continue
        ref[k.strip()] = v.strip()

    # normaliza aliases
    if "user" in ref and "user_id" not in ref:
        ref["user_id"] = ref["user"]
    if "pag" in ref and "pag_id" not in ref:
        ref["pag_id"] = ref["pag"]

    # >>> AQUI está o seu bug: você envia "plano:4" e o código espera "plano_id"
    if "plano" in ref and "plano_id" not in ref:
        ref["plano_id"] = ref["plano"]

    # (opcional) se você mandar "curso:10"
    if "curso" in ref and "curso_id" not in ref:
        ref["curso_id"] = ref["curso"]

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
      - JSON: {"action":"payment.updated","data":{"id":"123"}}
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
    Se não tiver secret configurado, retorna True (não bloqueia).
    """
    if not MERCADO_PAGO_WEBHOOK_SECRET:
        return True

    x_signature = request.headers.get("x-signature") or ""
    x_request_id = request.headers.get("x-request-id") or ""
    if not x_signature or not x_request_id:
        return False

    # x-signature: "ts=...,v1=..."
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
    """Consulta pagamento no MP: GET /v1/payments/{id}."""
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
# Rotas de verificação rápida (GET) e webhook real (POST)
# ---------------------------------------------------------------------
@router.get("/webhook")
def webhook_up():
    # isso te permite abrir no navegador e ver "webhook_up"
    return {"ok": True, "info": "webhook_up"}


@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook de pagamentos.
    Fluxo:
      1) extrai payment_id
      2) (opcional) valida assinatura
      3) consulta pagamento no MP
      4) localiza Pagamento no banco (por pag_id, mp_payment_id, external_reference)
      5) atualiza status e libera acesso se approved
    """
    # body pode não ser JSON
    body_json = None
    try:
        body_json = await request.json()
    except Exception:
        body_json = None

    payment_id = _extract_payment_id_from_request(request, body_json)
    if not payment_id:
        return {"ok": True, "ignored": "sem_payment_id"}

    if MERCADO_PAGO_WEBHOOK_SECRET:
        if not _verify_webhook_signature(request, payment_id):
            raise HTTPException(status_code=401, detail="Webhook signature inválida.")

    # consulta pagamento no MP
    try:
        mp = await _mp_get_payment(payment_id)
    except Exception:
        # no simulador do painel, o id costuma ser fake -> não derrubar
        return {"ok": True, "warning": "mp_get_failed", "payment_id": payment_id}

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    preference_id = mp.get("preference_id") or None

    ref = _parse_external_reference(external_reference)

    # tenta localizar pagamento no banco
    pagamento = None
    pag_id = ref.get("pag_id")

    # 1️⃣ Curso
    if isinstance(pag_id, int):
        pagamento = db.query(PagamentoCurso).filter(
            PagamentoCurso.id == pag_id
        ).first()

    # 2️⃣ Plano (somente se NÃO for curso)
    if not pagamento and isinstance(pag_id, int):
        pagamento = db.query(Pagamento).filter(
            Pagamento.id == pag_id
        ).first()


    # 2) fallback: por mp_payment_id (se existir no model)
    if not pagamento and hasattr(Pagamento, "mp_payment_id"):
        pagamento = db.query(Pagamento).filter(Pagamento.mp_payment_id == str(payment_id)).first()

    # 3) fallback: por external_reference (se existir campo no model)
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

    # Se não aprovado, só salva status
    if status != "approved":
        # mantém "pending", "rejected", "cancelled" etc
        pagamento.status = status
        db.commit()
        return {"ok": True, "status": status, "pagamento_id": pagamento.id}

    # -------------------------
    # APPROVED -> LIBERAÇÃO
    # -------------------------
    pagamento.status = "pago"
    db.commit()
    db.refresh(pagamento)

    usuario = db.query(Usuario).filter(Usuario.id == pagamento.usuario_id).first()
    if not usuario:
        return {"ok": True, "warning": "usuario_nao_encontrado", "pagamento_id": pagamento.id}

    # Define "kind" automaticamente quando o external_reference não manda kind=...
    kind = (ref.get("kind") or "").lower().strip()

    if not kind:
        # Se veio curso_id, então é curso
        if isinstance(ref.get("curso_id"), int):
            kind = "curso"
        # Se veio plano_id, então é plano
        elif isinstance(ref.get("plano_id"), int):
            kind = "plano"
        else:
            # fallback
            kind = "plano"

    # ---- PLANO
    if kind == "plano":
        periodo = (ref.get("periodo") or "mensal").lower()
        plano_id = ref.get("plano_id")

        # resolve nome do plano
        plano_nome = None
        if isinstance(plano_id, int):
            p = db.query(Plano).filter(Plano.id == plano_id).first()
            if p and p.nome:
                plano_nome = p.nome

        if not plano_nome:
            # fallback: usa o plano atual ou um padrão
            plano_nome = getattr(usuario, "plano_atual", None) or "Plano"

        # atualiza usuário
        if hasattr(usuario, "tipo_usuario"):
            # seu print mostra "Pendente" -> vira "Cliente"
            usuario.tipo_usuario = "Cliente"

        if hasattr(usuario, "plano_atual"):
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


    # ---- CURSO
    if kind == "curso":
        curso_id = ref.get("curso_id")

        if not isinstance(curso_id, int):
            return {
                "ok": True,
                "warning": "curso_id_invalido_ou_ausente",
                "usuario_id": usuario.id,
                "pagamento_id": pagamento.id,
                "external_reference": external_reference,
            }

        # Confirma se o curso existe (e opcionalmente se está ativo)
        curso = db.query(Curso).filter(Curso.id == curso_id).first()
        if not curso:
            return {
                "ok": True,
                "warning": "curso_nao_encontrado",
                "curso_id": curso_id,
                "usuario_id": usuario.id,
                "pagamento_id": pagamento.id,
            }

        # Idempotência: não duplica compra se webhook repetir
        ja = (
            db.query(CompraCurso)
            .filter(CompraCurso.usuario_id == usuario.id, CompraCurso.curso_id == curso_id)
            .first()
        )
        if ja:
            return {
                "ok": True,
                "liberado": "curso",
                "usuario_id": usuario.id,
                "curso_id": curso_id,
                "pagamento_id": pagamento.id,
                "observacao": "compra_ja_existia",
            }

        # Tenta pegar valor pago
        preco_pago = None
        try:
            # mais comum
            if mp.get("transaction_details") and mp["transaction_details"].get("total_paid_amount") is not None:
                preco_pago = float(mp["transaction_details"]["total_paid_amount"])
            elif mp.get("transaction_amount") is not None:
                preco_pago = float(mp["transaction_amount"])
        except Exception:
            preco_pago = None

        compra = CompraCurso(
            usuario_id=usuario.id,
            curso_id=curso_id,
            preco_pago=preco_pago if preco_pago is not None else 0.0,
            data_compra=datetime.utcnow(),
        )
        db.add(compra)
        db.commit()
        db.refresh(compra)

        return {
            "ok": True,
            "liberado": "curso",
            "usuario_id": usuario.id,
            "curso_id": curso_id,
            "pagamento_id": pagamento.id,
            "compra_id": compra.id,
            "preco_pago": compra.preco_pago,
        }




@router.post("/reprocessar")
async def reprocessar_pagamento_mp(
    payment_id: str,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    # ✅ Só admin pode usar
    if not getattr(usuario, "is_admin", False) and (getattr(usuario, "tipo_usuario", "") != "Admin"):
        raise HTTPException(status_code=403, detail="Apenas admin pode reprocessar pagamentos.")

    # consulta pagamento no MP e reutiliza a lógica do webhook
    mp = await _mp_get_payment(str(payment_id))

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    preference_id = mp.get("preference_id") or None

    ref = _parse_external_reference(external_reference)

    # localiza pagamento no banco
    pagamento = None
    pag_id = ref.get("pag_id")
    if isinstance(pag_id, int):
        pagamento = db.query(Pagamento).filter(Pagamento.id == pag_id).first()

    if not pagamento and hasattr(Pagamento, "mp_payment_id"):
        pagamento = db.query(Pagamento).filter(Pagamento.mp_payment_id == str(payment_id)).first()

    if not pagamento and external_reference and hasattr(Pagamento, "mp_external_reference"):
        pagamento = db.query(Pagamento).filter(Pagamento.mp_external_reference == external_reference).first()

    if not pagamento:
        return {
            "ok": False,
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

    if status != "approved":
        pagamento.status = status
        db.commit()
        return {"ok": True, "status": status, "pagamento_id": pagamento.id}

    # Se aprovado, marca e libera
    pagamento.status = "pago"
    db.commit()
    db.refresh(pagamento)

    usuario_pag = db.query(Usuario).filter(Usuario.id == pagamento.usuario_id).first()
    if not usuario_pag:
        return {"ok": False, "warning": "usuario_nao_encontrado", "pagamento_id": pagamento.id}

    # ✅ determina kind automaticamente
    kind = (ref.get("kind") or "").lower().strip()
    if not kind:
        if isinstance(ref.get("plano_id"), int):
            kind = "plano"
        elif isinstance(ref.get("curso_id"), int):
            kind = "curso"
        else:
            kind = "plano"

    # ---- PLANO
    if kind == "plano":
        periodo = (ref.get("periodo") or "mensal").lower()
        plano_id = ref.get("plano_id")

        plano_nome = None
        if isinstance(plano_id, int):
            p = db.query(Plano).filter(Plano.id == plano_id).first()
            if p and p.nome:
                plano_nome = p.nome

        if not plano_nome:
            plano_nome = getattr(usuario_pag, "plano_atual", None) or "Plano"

        if hasattr(usuario_pag, "tipo_usuario"):
            usuario_pag.tipo_usuario = "Cliente"
        if hasattr(usuario_pag, "plano_atual"):
            usuario_pag.plano_atual = plano_nome

        expira = datetime.utcnow() + (timedelta(days=365) if periodo == "anual" else timedelta(days=30))
        for campo in ("plano_expira_em", "plano_expira", "expira_em"):
            if hasattr(usuario_pag, campo):
                setattr(usuario_pag, campo, expira)
                break

        db.commit()
        return {"ok": True, "liberado": "plano", "usuario_id": usuario_pag.id, "plano": plano_nome}

    # ---- CURSO
    if kind == "curso":
        from backend.models.curso import Curso, CompraCurso  # import local para evitar conflito

        curso_id = ref.get("curso_id")
        if not isinstance(curso_id, int):
            return {"ok": False, "warning": "curso_id_invalido", "ref": ref}

        curso = db.query(Curso).filter(Curso.id == curso_id).first()
        if not curso:
            return {"ok": False, "warning": "curso_nao_encontrado", "curso_id": curso_id}

        ja = (
            db.query(CompraCurso)
            .filter(CompraCurso.usuario_id == usuario_pag.id, CompraCurso.curso_id == curso_id)
            .first()
        )
        if ja:
            return {"ok": True, "liberado": "curso", "curso_id": curso_id, "observacao": "compra_ja_existia"}

        preco_pago = None
        try:
            if mp.get("transaction_details") and mp["transaction_details"].get("total_paid_amount") is not None:
                preco_pago = float(mp["transaction_details"]["total_paid_amount"])
            elif mp.get("transaction_amount") is not None:
                preco_pago = float(mp["transaction_amount"])
        except Exception:
            preco_pago = None

        compra = CompraCurso(
            usuario_id=usuario_pag.id,
            curso_id=curso_id,
            preco_pago=preco_pago if preco_pago is not None else 0.0,
            data_compra=datetime.utcnow(),
        )
        db.add(compra)
        db.commit()
        db.refresh(compra)

        return {"ok": True, "liberado": "curso", "usuario_id": usuario_pag.id, "curso_id": curso_id, "compra_id": compra.id}

    return {"ok": True, "status": "approved_sem_kind", "pagamento_id": pagamento.id, "ref": ref}




@router.get("/__ping")
def ping():
    return {"ok": True}
