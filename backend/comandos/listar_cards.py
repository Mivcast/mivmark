# backend/comandos/listar_cards.py
import sys
import os
from datetime import datetime

# Garante que o projeto esteja no PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.database import engine
from backend.models import CardMarketing, Usuario
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

def listar_cards(usuario_id: int, mes: str):
    db = SessionLocal()
    try:
        print(f"📋 Listando cards do usuário {usuario_id} para o mês {mes}...\n")
        cards = (
            db.query(CardMarketing)
            .filter(
                CardMarketing.usuario_id == usuario_id,
                CardMarketing.mes_referencia == mes
            )
            .order_by(CardMarketing.criado_em.asc())
            .all()
        )

        if not cards:
            print("⚠️ Nenhum card encontrado.")
            return

        for c in cards:
            print(f"- [{c.id}] {c.titulo} | tipo={c.tipo} | favorito={c.favorito}")
    finally:
        db.close()

if __name__ == "__main__":
    # ajuste aqui o ID do usuário que você quer testar
    usuario_id = 1  # por exemplo
    mes = "2025-12"
    listar_cards(usuario_id, mes)
