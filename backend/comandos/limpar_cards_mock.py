import os
import sys
from sqlalchemy.orm import sessionmaker

# 🔧 Ajusta caminho raiz do projeto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, BASE_DIR)

from backend.database import engine
from backend.models import CardMarketing

SessionLocal = sessionmaker(bind=engine)


def limpar_mocks():
    db = SessionLocal()
    try:
        print("🔍 Removendo cards mockados por título...")

        padroes = [
            "Campanha: sites - Dica %",
            "Tendência: Atendimento com IA %",
            "Produto popular %",
            "Estatística relevante %",
            "Conteúdo estratégico %",
            "Desconto imperdível %",
            "Campanha do Bem %",
        ]

        total = 0
        for p in padroes:
            deletados = (
                db.query(CardMarketing)
                .filter(CardMarketing.titulo.like(p))
                .delete(synchronize_session=False)
            )
            if deletados:
                print(f"  • Removidos {deletados} cards com título LIKE '{p}'")
            total += deletados

        db.commit()
        print(f"✅ Total de cards mock removidos: {total}")

    except Exception as e:
        print("❌ Erro ao remover cards:", e)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    limpar_mocks()
