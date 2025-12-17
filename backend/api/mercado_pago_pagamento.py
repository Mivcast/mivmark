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
from backend.utils.email_utils import enviar_email


router = APIRouter(prefix="/mercado_pago", tags=["Mercado Pago"])

MP_ACCESS_TOKEN = (os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or "").strip()


def _mp_headers() -> Dict[str, str]:
    if not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado.")
    return {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}


def _parse_external_reference(ref: str) -> dict:
    """
    Formatos esperados (recomendado):
      plano:{plano_id}|periodo:{mensal/anual}|user:{user_id}|pag:{pagamento_id}|ts:{...}
      curso:{curso_id}|user:{user_id}|pag:{pagamento_id}|ts:{...}
    """
    out = {"raw": ref or ""}
    if not ref:
        return out

    def pick_int(pattern: str) -> Optional[int]:
        m = re.search(pattern, ref)
        return int(m.group(1)) if m else None

    def pick_str(pattern: str) -> Optional[str]:
        m = re.search(pattern, ref)
        return m.group(1) if m else None

    out["plano_id"] = pick_int(r"plano:(\d+)")
    out["curso_id"] = pick_int(r"curso:(\d+)")
    out["user_id"] = pick_int(r"user:(\d+)")
    out["pagamento_id"] = pick_int(r"pag:(\d+)")
    out["periodo"] = pick_str(r"periodo:([a-zA-Z_]+)")

    return out


async def _buscar_pagamento_mp(payment_id: str) -> Dict[str, Any]:
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=_mp_headers())
        if r.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Falha ao consultar pagamento no MP: {r.status_code} - {r.text}")
        return r.json()


def _email_compra_aprovada(usuario: Usuario, titulo: str, detalhes_html: str):
    assunto = f"✅ Pagamento aprovado — {titulo}"
    corpo = f"""
    <div style="font-family: Arial, sans-serif; line-height:1.5">
      <h2>Pagamento aprovado!</h2>
      <p>Olá, <b>{usuario.nome or "cliente"}</b>.</p>
      <p>Recebemos a confirmação do seu pagamento.</p>
      {detalhes_html}
      <p>Você já pode acessar o sistema com seu e-mail e senha normalmente.</p>
      <p style="margin-top:18px;">Atenciosamente,<br><b>MivMark</b></pを見る
    </div>
    """
    enviar_email(usuario.email, assunto, corpo, cc_admin=True)


@router.get("/__ping")
def mp_ping():
    return {"ok": True, "router": "mercado_pago_pagamento.py", "ts": datetime.utcnow().isoformat()}


@router.post("/webhook")
async def webhook_mercado_pago(request: Request, db: Session = Depends(get_db)):
    """
    Webhook público (sem auth).
    Mercado Pago pode enviar:
      - ?type=payment&data.id=123
      - ?topic=payment&id=123
      - corpo JSON com info semelhante
    """
    # 1) Coletar IDs de várias formas
    qp = dict(request.query_params)
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}

    payment_id = (
        qp.get("id")
        or qp.get("data.id")
        or (body.get("data") or {}).get("id")
        or body.get("id")
    )

    topic = (qp.get("topic") or qp.get("type") or body.get("type") or "").lower()

    if not payment_id:
        # MP às vezes manda ping/variações — responder 200 evita re-tentativas infinitas
        return {"ok": True, "ignored": True, "reason": "sem payment_id", "query": qp, "body": body}

    # 2) Buscar detalhes no MP (fonte da verdade)
    mp = await _buscar_pagamento_mp(str(payment_id))

    status = (mp.get("status") or "").lower()
    external_reference = mp.get("external_reference") or ""
    ref = _parse_external_reference(external_reference)

    print("[MP WEBHOOK] payment_id=", payment_id, "status=", status, "topic=", topic, "ref=", ref)

    if status != "approved":
        # Você pode tratar "in_process" etc, mas liberação automática só no approved
        return {"ok": True, "payment_id": payment_id, "status": status, "ref": ref}

    # 3) Idempotência / localizar pagamento interno
    pagamento_id = ref.get("pagamento_id")
    user_id = ref.get("user_id")

    pagamento = None
    if pagamento_id:
        pagamento = db.query(Pagamento).filter(Pagamento.id == int(pagamento_id)).first()

    # fallback: se não veio pagamento_id, tenta pelo user_id + status pendente mais recente
    if not pagamento and user_id:
        pagamento = (
            db.query(Pagamento)
            .filter(Pagamento.usuario_id == int(user_id))
            .order_by(Pagamento.id.desc())
            .first()
        )

    if pagamento:
        if (pagamento.status or "").lower() == "aprovado":
            return {"ok": True, "already_processed": True, "pagamento_id": pagamento.id}

        pagamento.status = "aprovado"
        pagamento.data_pagamento = datetime.utcnow()
        db.commit()

    # 4) Carregar usuário
    usuario = None
    if user_id:
        usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not usuario and pagamento:
        usuario = db.query(Usuario).filter(Usuario.id == int(pagamento.usuario_id)).first()

    if not usuario:
        # Não falhe o webhook (MP vai re-tentar); mas registre
        print("[MP WEBHOOK] Usuário não encontrado. user_id=", user_id, "pagamento=", getattr(pagamento, "id", None))
        return {"ok": True, "warning": "usuario_nao_encontrado", "ref": ref}

    # 5) Aplicar liberação (PLANO ou CURSO)
    if ref.get("plano_id"):
        periodo = (ref.get("periodo") or "mensal").lower()
        # Aqui usamos o nome que você gravou no Pagamento.plano (se existir)
        nome_plano = (pagamento.plano if pagamento else None) or "Plano"
        usuario.plano_atual = nome_plano

        if periodo == "anual":
            usuario.plano_expira_em = datetime.utcnow() + timedelta(days=365)
        else:
            usuario.plano_expira_em = datetime.utcnow() + timedelta(days=30)

        db.commit()

        _email_compra_aprovada(
            usuario,
            titulo=f"Plano {nome_plano}",
            detalhes_html=f"""
              <p><b>Plano:</b> {nome_plano}<br>
                 <b>Validade:</b> {usuario.plano_expira_em.strftime('%d/%m/%Y')}</p>
            """,
        )

        return {"ok": True, "liberado": "plano", "usuario_id": usuario.id, "plano": nome_plano}

    if ref.get("curso_id"):
        # IMPORTANTE: aqui depende de como você salva "curso comprado" no seu banco.
        # Eu deixei pronto para você plugar a sua tabela/modelo.
        curso_id = int(ref["curso_id"])

        # TODO: implementar gravação em tabela de cursos comprados quando você me mandar o backend/api/cursos.py (server-side)
        _email_compra_aprovada(
            usuario,
            titulo=f"Curso #{curso_id}",
            detalhes_html=f"<p><b>Curso:</b> #{curso_id}<br><b>Status:</b> Liberado para acesso</p>",
        )

        return {"ok": True, "liberado": "curso", "usuario_id": usuario.id, "curso_id": curso_id}

    # Se não veio plano/curso na referência, ainda assim avisamos e não quebramos
    return {"ok": True, "warning": "approved_sem_referencia", "payment_id": payment_id, "external_reference": external_reference}
