# backend/utils/email_utils.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_ORIGEM = "sitesmiv@gmail.com"
SENHA_APP = "SUA_SENHA_DE_APP_AQUI"  # Gere no painel do Gmail

def enviar_email(destinatario, assunto, corpo_html, corpo_texto=""):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_ORIGEM
    msg["To"] = destinatario

    parte_texto = MIMEText(corpo_texto or "Você recebeu um novo acesso.", "plain")
    parte_html = MIMEText(corpo_html, "html")

    msg.attach(parte_texto)
    msg.attach(parte_html)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(EMAIL_ORIGEM, SENHA_APP)
            servidor.sendmail(EMAIL_ORIGEM, destinatario, msg.as_string())
        print("✅ E-mail enviado com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
