from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx
import secrets
import random
import string
from database import SessionLocal
from models.tokens import TokenAtivacao
from models import Usuario
from utils.email_utils import enviar_email

router = APIRouter(prefix="/mercado_pago", tags=["Mercado Pago"])

ACCESS_TOKEN = "APP_USR-711759671777932-062712-4560f578d015b58d41b397a7322af76b-127583500"
WEBHOOK_URL = "https://SEUSITE.COM/webhook/mercado_pago"

# 🔹 MODELO ESPERADO NO BODY DA REQUISIÇÃO
class PagamentoInput(BaseModel):
    plano_nome: str
    preco: float

# ---------- ROTA PARA CRIAR PREFERÊNCIA DE PAGAMENTO ----------
@router.post("/criar_preferencia")
def criar_preferencia(dados: PagamentoInput):
    plano_nome = dados.plano_nome
    preco = dados.preco

    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "items": [{
            "title": f"Plano {plano_nome}",
            "quantity": 1,
            "unit_price": preco
        }],
        "notification_url": WEBHOOK_URL,
        "back_urls": {
            "success": "https://seusite.com/pagamento/sucesso",
            "failure": "https://seusite.com/pagamento/erro"
        },
        "auto_return": "approved"
    }

    response = httpx.post(url, json=body, headers=headers)
    if response.status_code != 201:
        raise HTTPException(status_code=500, detail="Erro ao criar preferência de pagamento")

    return {"init_point": response.json()["init_point"]}

# ---------- WEBHOOK DE PAGAMENTO ----------
@router.post("/webhook")
async def receber_pagamento(request: Request):
    data = await request.json()

    if data.get("type") != "payment":
        return {"status": "Ignorado"}

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return {"status": "Sem ID"}

    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    pagamento = httpx.get(url, headers=headers).json()

    if pagamento.get("status") != "approved":
        return {"status": "Pagamento não aprovado"}

    email = pagamento.get("payer", {}).get("email")
    nome = pagamento.get("payer", {}).get("first_name", "Novo usuário")
    plano = pagamento.get("description", "Plano Pago")

    token = secrets.token_hex(8)
    senha = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    db = SessionLocal()
    if db.query(Usuario).filter_by(email=email).first():
        return {"status": "Usuário já existe"}

    novo_token = TokenAtivacao(token=token)
    db.add(novo_token)
    db.commit()

    html = f"""
    <h2>🎉 Pagamento Aprovado!</h2>
    <p>Olá <strong>{nome}</strong>, seu pagamento do <b>{plano}</b> foi confirmado com sucesso!</p>
    <p>Agora você pode ativar sua conta com os dados abaixo:</p>
    <ul>
        <li><strong>Email:</strong> {email}</li>
        <li><strong>Senha provisória:</strong> {senha}</li>
        <li><strong>Token de ativação:</strong> {token}</li>
    </ul>
    <p>👉 Acesse: <a href="https://seusite.com">https://seusite.com</a></p>
    """

    try:
        enviar_email(email, f"Acesso ao Plano {plano}", html)
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

    return {"status": "Token enviado por e-mail"}
