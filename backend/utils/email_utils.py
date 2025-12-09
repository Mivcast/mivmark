# backend/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# 🔐 Dados do e-mail – configure no .env do backend / Render
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))  # SSL
EMAIL_USER = os.getenv("EMAIL_USER")  # ex: sitesmiv@gmail.com
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")      # senha de app do Gmail
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "MivMark - Sistema")
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN", EMAIL_USER)  # cópia para você, se quiser


def enviar_email(destinatario: str, assunto: str, corpo_html: str, corpo_texto: str = "") -> bool:
    """
    Envia um e-mail em HTML (e opcionalmente texto).
    Retorna True se deu certo, False se deu erro (não quebra o sistema).
    """

    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("[EMAIL] Variáveis de ambiente não configuradas. EMAIL_USER/EMAIL_PASSWORD ausentes.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
        msg["To"] = destinatario

        if corpo_texto:
            parte_texto = MIMEText(corpo_texto, "plain", "utf-8")
            msg.attach(parte_texto)

        parte_html = MIMEText(corpo_html, "html", "utf-8")
        msg.attach(parte_html)

        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, [destinatario], msg.as_string())

        print(f"[EMAIL] Enviado para {destinatario} - Assunto: {assunto}")
        return True

    except Exception as e:
        print(f"[EMAIL] Erro ao enviar e-mail para {destinatario}: {e}")
        return False


def enviar_email_simples(destinatario: str, assunto: str, mensagem: str) -> bool:
    """
    Atalho de compatibilidade (usado em alguns arquivos antigos).
    Envia apenas um texto simples, embrulhado em HTML básico.
    """
    corpo_html = f"<p>{mensagem}</p>"
    return enviar_email(destinatario, assunto, corpo_html, corpo_texto=mensagem)
