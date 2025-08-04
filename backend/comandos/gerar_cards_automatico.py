import sys
import os
from datetime import datetime, timedelta

# Garante que o diretório raiz esteja no caminho
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.database import engine
from backend.models import Usuario, CardMarketing
from sqlalchemy.orm import sessionmaker

from openai import OpenAI


openai.api_key = os.getenv("OPENAI_API_KEY")

SessionLocal = sessionmaker(bind=engine)

def buscar_novidades_do_nicho(nicho, mes):
    prompt = f"""
Você é um especialista em marketing digital.

Gere **10 ideias de cards** para uma Central de Marketing que apresenta **novidades, tendências, promoções e campanhas segmentadas** por nicho de mercado.

Nicho da empresa: **{nicho}**  
Mês de referência: **{mes}**

Distribua os cards de forma equilibrada entre os seguintes **tipos**:
- "Campanha"
- "Tendência"
- "Produto"
- "Dado"
- "Conteúdo"
- "Promoção"
- "Conscientização"

Cada card deve conter:
- Um **título curto e atrativo**
- Uma **descrição clara e útil**
- Um **link de fonte** (real ou fictício, exemplo: https://fonte.com/exemplo)
- 3 ideias de conteúdo separadas por linha
- Um tipo (exatamente como listado acima)

Formato de resposta:
[
  {{
    "titulo": "...",
    "descricao": "...",
    "fonte": "...",
    "ideias_conteudo": "1. ...\\n2. ...\\n3. ...",
    "tipo": "Tendência"
  }},
  ...
]
"""
    resposta = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        ideias = eval(resposta.choices[0].message.content.strip())
        return ideias
    except Exception as e:
        print("Erro ao processar resposta do GPT:", e)
        return []



def gerar_atualizacoes():
    db = SessionLocal()
    usuarios = db.query(Usuario).all()

    hoje = datetime.now()
    mes = (hoje + timedelta(days=3)).strftime("%Y-%m")

    for user in usuarios:
        if not user.empresa or not user.empresa.nicho:
            continue

        novidades = buscar_novidades_do_nicho(user.empresa.nicho, mes)

        for card in novidades:
            existe = db.query(CardMarketing).filter_by(
                usuario_id=user.id,
                titulo=card["titulo"],
                mes_referencia=mes
            ).first()

            if not existe:
                novo = CardMarketing(
                    usuario_id=user.id,
                    titulo=card["titulo"],
                    descricao=card["descricao"],
                    fonte=card["fonte"],
                    ideias_conteudo=card["ideias_conteudo"],
                    tipo=card["tipo"],
                    mes_referencia=mes,
                    favorito=False,
                    eh_atualizacao=True,
                    criado_em=datetime.now(),
                    atualizado_em=datetime.now()
                )
                db.add(novo)

    db.commit()
    db.close()
    print("✅ Atualizações com IA finalizadas.")

if __name__ == "__main__":
    gerar_atualizacoes()
