# backend/api/chat_publico.py
from fastapi import APIRouter, HTTPException, Query
from backend.database import SessionLocal
from backend.models import Empresa
from pydantic import BaseModel
from openai import OpenAI
import os

router = APIRouter()

# Cliente OpenAI (usa OPENAI_API_KEY do .env / Render)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class RespostaChat(BaseModel):
    resposta: str


def montar_contexto(empresa: Empresa) -> str:
    """
    Monta o texto de contexto para o atendente virtual,
    usando os dados reais da empresa.
    """
    partes = []

    partes.append(
        f"Você é um atendente virtual extremamente educado e objetivo da empresa "
        f"'{getattr(empresa, 'nome_empresa', '').strip()}'."
    )

    nicho = getattr(empresa, "nicho", "") or ""
    if nicho:
        partes.append(f"A empresa atua no nicho: {nicho}.")

    descricao = getattr(empresa, "descricao", "") or ""
    if descricao:
        partes.append(f"Descrição da empresa: {descricao}")

    cidade = getattr(empresa, "cidade", "") or ""
    bairro = getattr(empresa, "bairro", "") or ""
    rua = getattr(empresa, "rua", "") or ""
    numero = getattr(empresa, "numero", "") or ""
    if cidade or bairro or rua:
        partes.append(
            "Endereço aproximado: "
            f"{rua} {numero}, {bairro}, {cidade}."
        )

    whatsapp = getattr(empresa, "whatsapp", "") or ""
    if whatsapp:
        partes.append(f"WhatsApp para contato: {whatsapp}.")

    instagram = getattr(empresa, "instagram", "") or ""
    if instagram:
        partes.append(f"Instagram: {instagram}.")

    facebook = getattr(empresa, "facebook", "") or ""
    if facebook:
        partes.append(f"Facebook: {facebook}.")

    tiktok = getattr(empresa, "tiktok", "") or ""
    if tiktok:
        partes.append(f"TikTok: {tiktok}.")

    youtube = getattr(empresa, "youtube", "") or ""
    if youtube:
        partes.append(f"YouTube: {youtube}.")

    partes.append(
        "Responda sempre em primeira pessoa pela empresa, "
        "de forma simples, clara e amigável. "
        "Se não souber uma informação, diga que o cliente pode falar com a empresa "
        "pelo WhatsApp informado."
    )

    return "\n".join(partes)


@router.get("/chat_publico/perguntar", response_model=RespostaChat)
def perguntar(pergunta: str = Query(...), empresa: str = Query(...)):
    """
    Endpoint simples para o widget público do site.
    Recebe ?pergunta=...&empresa=Nome ou slug da empresa.
    """
    if not pergunta.strip():
        raise HTTPException(status_code=400, detail="Pergunta vazia.")

    db = SessionLocal()
    try:
        # Tenta achar a empresa pelo nome aproximado ou slug
        filtro = f"%{empresa.replace('_', ' ').strip()}%"
        empresa_obj = (
            db.query(Empresa)
            .filter(Empresa.nome_empresa.ilike(filtro))
            .first()
        )

        if not empresa_obj:
            raise HTTPException(status_code=404, detail="Empresa não encontrada.")

        contexto = montar_contexto(empresa_obj)

        # Chamada usando a API nova
        resposta_api = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user", "content": pergunta},
            ],
            temperature=0.4,
            max_tokens=400,
        )

        texto = resposta_api.choices[0].message.content.strip()
        return RespostaChat(resposta=texto)

    except HTTPException:
        raise
    except Exception as e:
        # Retorna erro mas sem quebrar o site
        return RespostaChat(
            resposta=f"Desculpe, ocorreu um erro ao responder: {e}"
        )
    finally:
        db.close()
