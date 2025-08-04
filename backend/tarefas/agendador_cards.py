import sys
import os
import random
from datetime import datetime, timedelta

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")  # ou defina diretamente se preferir



# Garante que o diretório raiz esteja no caminho
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.database import engine
from backend.models import Usuario, CardMarketing
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

def buscar_novidades_do_nicho(nicho: str, mes: str):
    prompt = f"""
    Gere 10 cards de marketing para o nicho "{nicho}", no mês de referência "{mes}".
    Cada card deve conter:
    - título
    - descrição
    - fonte (simulada ou real)
    - ideias_conteudo (3 ideias em tópicos)
    - tipo (Campanha, Promoção, Tendência, Produto, Dado, Conteúdo ou Conscientização)

    Responda em JSON com uma lista de dicionários.
    """

    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    texto = resposta.choices[0].message.content

    # Convertendo resposta JSON em lista Python
    try:
        import json
        cards = json.loads(texto)
        return cards
    except:
        print("Erro ao interpretar resposta do GPT:", texto)
        return []


def gerar_atualizacoes():
    db = SessionLocal()
    usuarios = db.query(Usuario).all()

    # Gera para o mês atual ou próximo (dependendo da data)
    hoje = datetime.now()
    mes = (hoje + timedelta(days=3)).strftime("%Y-%m")

    for user in usuarios:
        if not user.empresa or not user.empresa.nicho:
            continue

        novidades = buscar_novidades_do_nicho(user.empresa.nicho)

        for n in novidades:
            existe = db.query(CardMarketing).filter_by(
                usuario_id=user.id,
                titulo=n["titulo"],
                mes_referencia=mes
            ).first()

            if not existe:
                novo_card = CardMarketing(
                    usuario_id=user.id,
                    titulo=n["titulo"],
                    descricao=n["descricao"],
                    fonte=n["fonte"],
                    ideias_conteudo=n["ideias_conteudo"],
                    tipo=n["tipo"],
                    mes_referencia=mes,
                    eh_atualizacao=True,
                    criado_em=datetime.now(),
                    atualizado_em=datetime.now()
                )
                db.add(novo_card)

    db.commit()
    db.close()
    print("✅ Atualizações diárias finalizadas.")

if __name__ == "__main__":
    gerar_atualizacoes()
