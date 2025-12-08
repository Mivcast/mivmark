import sys
import os
import json
from datetime import datetime, timedelta


# 🔹 Garante que o diretório raiz esteja no caminho
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.database import engine
from backend.models import Usuario, CardMarketing
from sqlalchemy.orm import sessionmaker

from openai import OpenAI
from dotenv import load_dotenv  # ✅ para ler o .env

# 🔹 Carrega variáveis do .env
load_dotenv()

# ⚙️ Cliente OpenAI
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    print("❌ ERRO: OPENAI_API_KEY não encontrada nas variáveis de ambiente nem no .env.")
    print("   Verifique se o arquivo .env na raiz tem algo como:")
    print("   OPENAI_API_KEY=suachave_aqui")
    raise SystemExit(1)

client = OpenAI(api_key=OPENAI_KEY)

SessionLocal = sessionmaker(bind=engine)


def buscar_novidades_do_nicho(nicho: str, mes: str):
    """
    Chama o GPT pedindo 10 ideias de cards em formato de LISTA JSON.
    Retorna uma lista de dicionários prontos para salvar no banco.
    """

    prompt = f"""
Você é um especialista em marketing digital.

Gere EXATAMENTE 10 cards para uma Central de Marketing que apresenta
novidades, tendências, promoções e campanhas segmentadas por nicho de mercado.

Nicho da empresa: "{nicho}"
Mês de referência (ano-mês): "{mes}"

Distribua os cards de forma equilibrada entre os seguintes tipos:
- "Campanha"
- "Tendência"
- "Produto"
- "Dado"
- "Conteúdo"
- "Promoção"
- "Conscientização"

Cada card deve conter campos com estes nomes EXATOS:
- "titulo": título curto e atrativo
- "descricao": descrição clara e útil
- "fonte": link de fonte (real ou fictício, ex: "https://exemplo.com/materia")
- "ideias_conteudo": string com 3 ideias de conteúdo, uma por linha, no formato:
  "1. ...\\n2. ...\\n3. ..."
- "tipo": um dos tipos listados acima

RESPOSTA OBRIGATÓRIA:
Retorne APENAS uma LISTA JSON, SEM explicações antes ou depois, assim:

[
  {{
    "titulo": "...",
    "descricao": "...",
    "fonte": "https://...",
    "ideias_conteudo": "1. ...\\n2. ...\\n3. ...",
    "tipo": "Tendência"
  }},
  ...
]
"""

    resposta = client.chat.completions.create(
        model="gpt-4.1-mini",  # pode trocar para o modelo que você já usa
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )

    conteudo = resposta.choices[0].message.content.strip()

    # 🔍 Debug opcional
    print("==== RESPOSTA BRUTA DO GPT (primeiros 1000 caracteres) ====")
    print(conteudo[:1000])
    print("==== FIM RESPOSTA BRUTA ====")

    try:
        # Tenta achar apenas o trecho entre [ ... ]
        inicio = conteudo.find("[")
        fim = conteudo.rfind("]") + 1

        if inicio == -1 or fim == 0:
            raise ValueError("Não foi encontrado um JSON de lista entre colchetes.")

        json_puro = conteudo[inicio:fim]

        ideias = json.loads(json_puro)

        if not isinstance(ideias, list):
            raise ValueError("O JSON retornado não é uma lista.")

        # 🔎 Garantir que cada item é um dict com as chaves esperadas
        cards_limpos = []
        for i, card in enumerate(ideias, start=1):
            if not isinstance(card, dict):
                print(f"[AVISO] Item {i} não é dict, ignorando:", card)
                continue

            titulo = card.get("titulo", "").strip()
            descricao = card.get("descricao", "").strip()
            fonte = card.get("fonte", "").strip() or "https://exemplo.com"
            ideias_conteudo = card.get("ideias_conteudo", "").strip()
            tipo = card.get("tipo", "").strip() or "Conteúdo"

            if not titulo or not descricao:
                print(f"[AVISO] Card {i} sem título ou descrição, ignorando.")
                continue

            cards_limpos.append(
                {
                    "titulo": titulo,
                    "descricao": descricao,
                    "fonte": fonte,
                    "ideias_conteudo": ideias_conteudo,
                    "tipo": tipo,
                }
            )

        print(f"✅ {len(cards_limpos)} cards válidos gerados para o nicho '{nicho}'.")
        return cards_limpos

    except Exception as e:
        print("❌ Erro ao processar resposta do GPT:", e)
        return []


def gerar_atualizacoes():
    """
    Percorre todos os usuários, verifica o nicho da empresa e gera cards
    para o mês atual, sem duplicar títulos no mesmo mês.
    """

    db = SessionLocal()

    try:
        usuarios = db.query(Usuario).all()

        hoje = datetime.now()
        # 👉 Mês atual no formato YYYY-MM
        mes = hoje.strftime("%Y-%m")

        print("=======================================")
        print(f"🗓  Gerando cards automáticos para o mês: {mes}")
        print("=======================================")

        for user in usuarios:
            if not getattr(user, "empresa", None) or not getattr(
                user.empresa, "nicho", None
            ):
                print(
                    f"- Usuário {user.id} sem empresa ou nicho configurado. Pulando..."
                )
                continue

            nicho = user.empresa.nicho
            print(f"\n👤 Usuário {user.id} | Nicho: {nicho}")

            novidades = buscar_novidades_do_nicho(nicho, mes)

            if not novidades:
                print(f"⚠️ Nenhum card retornado pelo GPT para o usuário {user.id}.")
                continue

            novos_cards = 0

            for card in novidades:
                existe = (
                    db.query(CardMarketing)
                    .filter_by(
                        usuario_id=user.id,
                        titulo=card["titulo"],
                        mes_referencia=mes,
                    )
                    .first()
                )

                if existe:
                    print(f"  • Já existe card com título: {card['titulo']}")
                    continue

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
                    atualizado_em=datetime.now(),
                )
                db.add(novo)
                novos_cards += 1
                print(f"  ✅ Card criado: {card['titulo']}")

            if novos_cards == 0:
                print(f"ℹ️ Nenhum novo card foi criado para o usuário {user.id}.")
            else:
                print(f"🎉 Total de {novos_cards} novos cards para o usuário {user.id}.")

        db.commit()
        print("\n✅ Atualizações com IA finalizadas.\n")

    except Exception as e:
        db.rollback()
        print("❌ Erro geral ao gerar atualizações:", e)

    finally:
        db.close()


if __name__ == "__main__":
    gerar_atualizacoes()
