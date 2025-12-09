# backend/api/email_teste.py

from fastapi import APIRouter
from backend.utils.email_utils import enviar_email

router = APIRouter(prefix="/email", tags=["Testes de E-mail"])


@router.get("/teste")
def teste_email(destino: str = None):
    """
    Envia um e-mail de teste simples.
    Exemplo: /email/teste?destino=seuemail@gmail.com
    """

    if not destino:
        return {"erro": "Use /email/teste?destino=seuemail@gmail.com"}

    assunto = "🎯 Teste de E-mail – MivMark"
    mensagem = f"""
    <p>Olá!</p>
    <p>Este é um e-mail de <strong>teste</strong> enviado pelo MivMark.</p>
    <p>Se você recebeu esta mensagem, o servidor de e-mail está configurado corretamente.</p>
    <br/>
    <p>✔ Servidor: OK</p>
    <p>✔ Variáveis do Render: OK</p>
    <p>✔ Biblioteca SMTP: OK</p>
    """

    sucesso = enviar_email(destino, assunto, mensagem)

    if sucesso:
        return {
            "status": "ok",
            "mensagem": f"E-mail enviado com sucesso para {destino}."
        }

    return {
        "status": "erro",
        "mensagem": "Falha ao enviar e-mail. Verifique variáveis de ambiente."
    }
