# backend/api/mercado_pago.py

import os
import logging
from datetime import datetime

import requests
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from backend.database import get_db
from backend.models import Usuario, Pagamento, TokenAtivacao

# Se quiser usar e-mail depois, podemos aproveitar esse util
try:
    from backend.utils.email_utils import enviar_email_simples
except Exception:
    enviar_email_simples = None

router = APIRouter()

MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")


def buscar_pagamento_mp(payment_id: str):
    """
    Consulta a API do Mercado Pago para obter os detalhes do pagamento.
    """
    if not MERCADO_PAGO_ACCESS_TOKEN:
        logging.error("MERCADO_PAGO_ACCESS_TOKEN não definido no .env")
        return None

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {
        "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        logging.error(f"Erro ao consultar pagamento {payment_id}: {resp.status_code} {resp.text}")
        return None

    return resp.json()


def identificar_plano_consultoria_por_titulo(title: str) -> str | None:
    """
    Recebe o título do item do Mercado Pago e devolve o nome do plano interno.
    Por enquanto, qualquer consultoria cai no plano 'consultoria_full'.
    Se quiser diferenciar depois (essencial/impulso/etc), é só ajustar aqui.
    """
    if not title:
        return None

    title_lower = title.lower()

    if "consultoria empresarial" in title_lower and "mivmark" in title_lower:
        # No futuro, podemos diferenciar:
        # if "essencial" in title_lower: return "consultoria_essencial"
        # etc...
        return "consultoria_full"

    return None


def criar_ou_obter_usuario_por_email(db: Session, email: str) -> Usuario:
    """
    Busca usuário pelo e-mail; se não existir, cria um básico.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario:
        return usuario

    nome = email.split("@")[0] if email else "Cliente MivMark"

    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash="",  # depois ele poderá definir/recuperar a senha
        tipo_usuario="cliente",
        plano_atual=None,
        data_criacao=datetime.utcnow(),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def gerar_token_consultoria(db: Session, usuario: Usuario, nome_plano: str = "consultoria_full") -> TokenAtivacao:
    """
    Gera um token de ativação vinculado ao usuário e ao plano da consultoria.
    Validade padrão: 365 dias.
    """
    token = TokenAtivacao.gerar_token(
        usuario_id=usuario.id,
        plano=nome_plano,
        dias_validade=365,
    )
    db.add(token)

    # Atualiza plano do usuário para vigorar pelo mesmo período do token
    usuario.plano_atual = nome_plano
    usuario.plano_expira_em = token.expira_em

    db.commit()
    db.refresh(usuario)
    db.refresh(token)
    return token


def registrar_pagamento(
    db: Session,
    usuario: Usuario,
    plano: str,
    valor: float,
    gateway: str = "mercado_pago",
    status: str = "approved",
):
    """
    Cria um registro na tabela pagamentos.
    """
    pagamento = Pagamento(
        usuario_id=usuario.id,
        plano=plano,
        valor=valor,
        status=status,
        gateway=gateway,
        data_pagamento=datetime.utcnow(),
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)
    return pagamento


def enviar_email_boas_vindas_consultoria(usuario: Usuario, token: TokenAtivacao):
    """
    Envia e-mail com o token e orientações de acesso.
    Só funciona se enviar_email_simples estiver implementado.
    """
    if not enviar_email_simples:
        logging.warning("Função enviar_email_simples não encontrada. E-mail não enviado.")
        return

    assunto = "Acesso à Consultoria Empresarial MivMark"
    corpo = f"""
Olá, {usuario.nome}!

Seu pagamento da Consultoria Empresarial foi aprovado. 🎉

Agora você tem acesso ao sistema MivMark por 1 ano, com o plano de consultoria.

Para acessar:

1. Acesse o MivMark pelo link que o Matheus informar.
2. Faça login com seu e-mail: {usuario.email}
3. No primeiro acesso, use a opção "Tenho um token de ativação" (quando estiver disponível).
4. Use este token:

    {token.token}

Seu plano ficará ativo até: {token.expira_em.strftime("%d/%m/%Y")}.

Qualquer dúvida, entre em contato com a MivCast.

Abraço,
Equipe MivMark / MivCast
"""

    try:
        enviar_email_simples(destinatario=usuario.email, assunto=assunto, corpo=corpo)
    except Exception as e:
        logging.error(f"Erro ao enviar e-mail de boas-vindas: {e}")


@router.post("/mercado-pago/webhook")
async def webhook_mercado_pago(request: Request, db: Session = Depends(get_db)):
    """
    Webhook chamado pelo Mercado Pago quando há eventos de pagamento.
    Aqui é onde reconhecemos a compra de uma consultoria e liberamos acesso ao MivMark.
    """
    payload = await request.json()
    logging.info(f"🔔 Webhook Mercado Pago recebido: {payload}")

    # Exemplo de payload:
    # { "type": "payment", "data": { "id": "123456789" } }
    if payload.get("type") != "payment":
        # Outros tipos (plan, subscription etc.) podem ser tratados no futuro
        return JSONResponse(content={"status": "ignored", "detail": "tipo não suportado"}, status_code=200)

    payment_id = payload.get("data", {}).get("id")
    if not payment_id:
        return JSONResponse(content={"status": "error", "detail": "payment id ausente"}, status_code=400)

    pagamento_mp = buscar_pagamento_mp(payment_id)
    if not pagamento_mp:
        return JSONResponse(content={"status": "error", "detail": "não foi possível consultar o pagamento"}, status_code=500)

    status_pagamento = pagamento_mp.get("status")
    if status_pagamento != "approved":
        # Se não estiver aprovado, não faz nada
        logging.info(f"Pagamento {payment_id} com status {status_pagamento}. Nada a fazer ainda.")
        return JSONResponse(content={"status": "ok", "detail": f"pagamento {status_pagamento}"}, status_code=200)

    # Título do item comprado
    items = pagamento_mp.get("additional_info", {}).get("items", [])
    title = items[0].get("title") if items else ""

    # Valor
    valor = pagamento_mp.get("transaction_amount", 0.0)

    # E-mail do pagador
    payer = pagamento_mp.get("payer", {})
    email_pagador = payer.get("email") or ""

    # Identifica se é uma consultoria MivMark
    nome_plano_interno = identificar_plano_consultoria_por_titulo(title)
    if not nome_plano_interno:
        logging.info(f"Pagamento {payment_id} não corresponde a consultoria MivMark (title: {title}).")
        return JSONResponse(content={"status": "ok", "detail": "não é consultoria"}, status_code=200)

    # Cria ou encontra o usuário
    usuario = criar_ou_obter_usuario_por_email(db, email_pagador)

    # Gera token e atualiza plano do usuário por 1 ano
    token = gerar_token_consultoria(db, usuario, nome_plano_interno)

    # Registra pagamento
    registrar_pagamento(db, usuario, plano=nome_plano_interno, valor=valor)

    # Envia e-mail com token (se tiver função configurada)
    enviar_email_boas_vindas_consultoria(usuario, token)

    logging.info(f"✅ Consultoria liberada para o usuário {usuario.email} (plano {nome_plano_interno}).")

    return JSONResponse(content={"status": "ok"}, status_code=200)

