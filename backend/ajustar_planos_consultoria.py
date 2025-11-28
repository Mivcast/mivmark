from .database import SessionLocal
from .models import Usuario  # 👈 aqui é o ajuste

def ajustar_planos():
    db = SessionLocal()
    try:
        usuarios = (
            db.query(Usuario)
            .filter(Usuario.plano_atual == "consultoria_full")
            .all()
        )
        print(f"Encontrados {len(usuarios)} usuários com plano 'consultoria_full'.")

        for u in usuarios:
            print(f"Ajustando usuário {u.id} - {u.email} de 'consultoria_full' para 'Profissional'")
            u.plano_atual = "Profissional"

        db.commit()
        print("Ajuste concluído com sucesso.")
    except Exception as e:
        db.rollback()
        print("Erro ao ajustar planos:", e)
    finally:
        db.close()

if __name__ == "__main__":
    ajustar_planos()
