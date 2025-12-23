# backend/api/planos.py

from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Literal, Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_usuario_logado
from backend.models import Usuario, Pagamento
from backend.models.planos import Plano, PlanoSchema, PlanoCreate
from backend.models.cupom import CupomDesconto

router = APIRouter(prefix="/planos", tags=["Planos"])

# =========================================================
# Mercado Pago (mesmo padrão do cursos.py)
# =========================================================
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "").strip().rstrip("/")


def _mp_notification_url() -> Optional[str]:
    if not BACKEND_URL:
        return None
    # Seu webhook real (router prefix="/mercado_pago")
    return f"{BACKEND_URL}/mercado_pago/webhook"


def criar_preferencia_mp(
    titulo: str,
    valor: float,
    referencia_externa: str,
    payer_email: str,
    payer_first_name: str = "",
    payer_last_name: str = "",
    item_id: str = "",
    item_description: str = "",
    category_id: str = "services",
) -> dict:
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no ambiente.")

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # -------------------------
    # Back URLs (melhor para qualidade/score)
    # -------------------------
    back_urls = None
    if FRONTEND_URL:
        base = FRONTEND_URL.rstrip("/")
        back_urls = {
            "success": f"{base}/?mp=success",
            "failure": f"{base}/?mp=failure",
            "pending": f"{base}/?mp=pending",
        }

    # -------------------------
    # Item completo (id, description, category_id etc.)
    # -------------------------
    item = {
        "id": item_id or referencia_externa[:50],  # fallback simples
        "title": titulo,
        "description": item_description or titulo,
        "category_id": category_id or "services",
        "quantity": 1,
        "unit_price": float(valor),
        "currency_id": "BRL",
    }

    body = {
        "items": [item],
        "external_reference": referencia_externa,

        # Buyer (ajuda muito na qualidade)
        "payer": {
            "email": payer_email,
            "name": payer_first_name or "",
            "surname": payer_last_name or "",
        },

        # Metadata para conciliação/debug
        "metadata": {
            "external_reference": referencia_externa,
            "tipo": "plano",
        },
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
# Helpers cupom
# =========================================================
def _cupom_expirado(valido_ate) -> bool:
    if not valido_ate:
        return False
    if isinstance(valido_ate, datetime):
        return valido_ate.date() < date.today()
    if isinstance(valido_ate, date):
        return valido_ate < date.today()
    return False


def _normalizar_codigo(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    c = (c or "").strip().lower()
    return c or None


def _cupom_valido_para_plano(cupom: CupomDesconto, plano: Plano) -> bool:
    """
    Regras:
    - Cupom escopo="plano"
    - cupom.plano_nome:
        - None/"" => vale para todos
        - "todos" => vale para todos
        - outro => precisa bater com plano.nome (case-insensitive)
    """
    alvo = (cupom.plano_nome or "").strip().lower()
    if not alvo or alvo == "todos":
        return True
    return alvo == (plano.nome or "").strip().lower()


# =========================================================
# CRUD de Planos
# =========================================================
@router.get("/", response_model=List[PlanoSchema])
def listar_planos(db: Session = Depends(get_db)):
    return db.query(Plano).order_by(Plano.id.asc()).all()


@router.post("/", response_model=PlanoSchema)
def criar_plano(plano: PlanoCreate, db: Session = Depends(get_db)):
    novo = Plano(**plano.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.put("/{plano_id}", response_model=PlanoSchema)
def atualizar_plano(plano_id: int, plano: PlanoCreate, db: Session = Depends(get_db)):
    db_plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not db_plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    for campo, valor in plano.model_dump().items():
        setattr(db_plano, campo, valor)

    db.commit()
    db.refresh(db_plano)
    return db_plano


@router.delete("/{plano_id}")
def excluir_plano(plano_id: int, db: Session = Depends(get_db)):
    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    db.delete(plano)
    db.commit()
    return {"ok": True}


# =========================================================
# Compra de Plano (Cupom + Mercado Pago)
# =========================================================
@router.post("/{plano_id}/comprar")
def comprar_plano(
    plano_id: int,
    cupom: Optional[str] = Query(default=None),
    periodo: Literal["mensal", "anual"] = Query(default="mensal"),
    quantidade: int = Query(default=1, ge=1, le=12),  # 👈 NOVO
    metodo: Literal["pix", "cartao"] = Query(default="pix"),
    gateway: str = Query(default="mercado_pago"),
    debug: bool = Query(default=False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    dbg: Dict[str, Any] = {}

    dbg["plano_id"] = plano_id
    dbg["cupom_recebido"] = cupom
    dbg["periodo"] = periodo
    dbg["quantidade"] = quantidade
    dbg["metodo"] = metodo
    dbg["gateway"] = gateway

    plano = db.query(Plano).filter(Plano.id == plano_id).first()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    dbg["plano_nome"] = plano.nome

    # -------------------------------------------------
    # 1) CALCULA VALOR BASE
    # -------------------------------------------------
    preco_mensal = float(plano.preco_mensal or 0.0)
    preco_anual = float(plano.preco_anual or 0.0)

    if periodo == "anual":
        # anual sempre é 12 meses
        valor = preco_anual if preco_anual > 0 else preco_mensal * 12
        meses = 12
    else:
        # mensal com quantidade (1, 3, 6)
        valor = preco_mensal * quantidade
        meses = quantidade

    # -------------------------------------------------
    # 1.1) DESCONTO POR PERÍODO (V1)
    # - 3 meses: 5%
    # - 6 meses: 10%
    # - anual: NÃO aplica aqui (usa preco_anual do banco)
    # -------------------------------------------------
    desconto_periodo_pct = 0.0

    if periodo == "mensal":
        if quantidade == 3:
            desconto_periodo_pct = 5.0
        elif quantidade == 6:
            desconto_periodo_pct = 10.0

    # aplica desconto do período (somente mensal 3/6)
    if desconto_periodo_pct > 0:
        valor = valor * (1 - desconto_periodo_pct / 100.0)

    dbg["desconto_periodo_pct_backend"] = desconto_periodo_pct
    dbg["valor_pos_desconto_periodo"] = float(valor)




    dbg["valor_base"] = float(valor)
    dbg["meses"] = meses

    if valor <= 0:
        raise HTTPException(status_code=400, detail="Plano com preço inválido (0).")

    # -------------------------------------------------
    # 2) VALIDA CUPOM (escopo=plano)
    # -------------------------------------------------
    codigo_cupom = _normalizar_codigo(cupom)
    dbg["codigo_normalizado"] = codigo_cupom

    if codigo_cupom:
        c = (
            db.query(CupomDesconto)
            .filter(
                func.lower(func.trim(CupomDesconto.codigo)) == codigo_cupom,
                CupomDesconto.ativo.is_(True),
                func.lower(func.trim(CupomDesconto.escopo)) == "plano",
            )
            .first()
        )

        if debug:
            ultimos = (
                db.query(
                    CupomDesconto.id,
                    CupomDesconto.codigo,
                    CupomDesconto.escopo,
                    CupomDesconto.ativo,
                    CupomDesconto.plano_nome,
                )
                .order_by(CupomDesconto.id.desc())
                .limit(20)
                .all()
            )
            dbg["cupons_ultimos_20"] = [
                {
                    "id": x[0],
                    "codigo": x[1],
                    "escopo": x[2],
                    "ativo": x[3],
                    "plano_nome": x[4],
                }
                for x in ultimos
            ]

        if not c:
            if debug:
                return {"ok": False, "erro": "cupom_nao_encontrado", "debug": dbg}
            raise HTTPException(status_code=400, detail="Cupom inválido.")

        if _cupom_expirado(c.valido_ate):
            if debug:
                return {"ok": False, "erro": "cupom_expirado", "debug": dbg}
            raise HTTPException(status_code=400, detail="Cupom expirado.")

        if not _cupom_valido_para_plano(c, plano):
            if debug:
                return {"ok": False, "erro": "cupom_nao_valido_para_plano", "debug": dbg}
            raise HTTPException(status_code=400, detail="Cupom não válido para este plano.")

        desconto = float(c.desconto_percent or 0.0)
        dbg["desconto_percent"] = desconto

        if desconto <= 0 or desconto > 100:
            if debug:
                return {"ok": False, "erro": "desconto_invalido", "debug": dbg}
            raise HTTPException(status_code=400, detail="Cupom com desconto inválido.")

        valor = valor * (1 - desconto / 100.0)

    valor = round(float(valor), 2)
    dbg["valor_final"] = valor

    # -------------------------------------------------
    # 3) CUPOM 100% → LIBERA NA HORA
    # -------------------------------------------------
    if valor <= 0.01:
        usuario.plano_atual = plano.nome
        usuario.plano_expira_em = datetime.utcnow() + timedelta(days=30 * meses)
        db.commit()

        out = {"mensagem": "Plano liberado com cupom de 100%."}
        if debug:
            out["debug"] = dbg
        return out

    # -------------------------------------------------
    # 4) CRIA PAGAMENTO PENDENTE
    # -------------------------------------------------
    pagamento = Pagamento(
        usuario_id=usuario.id,
        plano=plano.nome,
        valor=valor,
        status="pendente",
        gateway=gateway,
        data_pagamento=datetime.utcnow(),
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    # -------------------------------------------------
    # 5) MERCADO PAGO
    # -------------------------------------------------
    referencia = (
        f"plano:{plano.id}|"
        f"periodo:{periodo}|"
        f"qtd:{quantidade}|"
        f"user:{usuario.id}|"
        f"pag:{pagamento.id}|"
        f"ts:{int(datetime.utcnow().timestamp())}"
    )

    titulo = f"Plano {plano.nome} ({meses} meses)"

    # item_id (SKU interno)
    item_id = f"plano_{plano.id}_{periodo}"

    # description curta e clara
    descricao = f"Assinatura do Plano {plano.nome} ({periodo}). Acesso ao sistema MivMark."

    # nome/sobrenome (se você tiver no model Usuario; se não tiver, deixa vazio)
    primeiro_nome = getattr(usuario, "nome", "") or ""
    sobrenome = getattr(usuario, "sobrenome", "") or ""

    pref = criar_preferencia_mp(
        titulo=f"Plano {plano.nome} ({periodo})",
        valor=float(valor),
        referencia_externa=referencia,
        payer_email=usuario.email,
        payer_first_name=primeiro_nome,
        payer_last_name=sobrenome,
        item_id=item_id,
        item_description=descricao,
        category_id="services",
    )


    resp = {
        "mensagem": "Link de pagamento gerado",
        "pagamento_id": pagamento.id,
        "valor": valor,
        "status": "aguardando",
        "init_point": pref.get("init_point"),
        "preference_id": pref.get("preference_id"),
    }

    if debug:
        resp["debug"] = dbg

    return resp



@router.get("/__ping")
def planos_ping():
    return {"ok": True, "router": "planos.py carregado", "ts": datetime.utcnow().isoformat()}
