# backend/utils/email_utils.py

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USER = os.getenv("EMAIL_USER", "sitesmiv@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "mmft fmgw nlws bzpo")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "MivMark - Sistema")
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN", EMAIL_USER)


def enviar_email(destinatario: str, assunto: str, corpo_html: str, corpo_texto: str | None = None, cc_admin: bool = False) -> bool:
    """
    Envia e-mail via SMTP SSL (Gmail).
    Requer: EMAIL_USER e EMAIL_PASSWORD (senha de app).
    """
    try:
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("[EMAIL] EMAIL_USER/EMAIL_PASSWORD não configurados. Abortando envio.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
        msg["To"] = destinatario

        if cc_admin and EMAIL_ADMIN:
            msg["Cc"] = EMAIL_ADMIN
            destinatarios = [destinatario, EMAIL_ADMIN]
        else:
            destinatarios = [destinatario]

        if corpo_texto:
            msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))

        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, destinatarios, msg.as_string())

        print(f"[EMAIL] Enviado para {destinatario} (cc_admin={cc_admin})")
        return True

    except Exception as e:
        print(f"[EMAIL] Erro ao enviar e-mail para {destinatario}: {e}")
        return False


def enviar_email_simples(destinatario: str, assunto: str, mensagem: str) -> bool:
    corpo_html = f"<p>{mensagem}</p>"
    return enviar_email(destinatario, assunto, corpo_html, corpo_texto=mensagem)
