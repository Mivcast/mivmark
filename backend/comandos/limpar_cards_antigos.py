import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.database import engine
from backend.models import CardMarketing
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

def limpar_cards_genericos():
    db = SessionLocal()
    try:
        # Ajuste o filtro para pegar só os cards que você sabe que são "antigos"
        deletados = (
            db.query(CardMarketing)
            .filter(CardMarketing.eh_atualizacao == False)  # antigos / mock
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"✅ {deletados} cards antigos removidos.")
    finally:
        db.close()

if __name__ == "__main__":
    limpar_cards_genericos()
