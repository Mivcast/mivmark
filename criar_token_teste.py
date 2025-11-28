from datetime import datetime, timedelta
from backend.database import SessionLocal
from backend.models import Usuario, TokenAtivacao

EMAIL_USUARIO = "sitesmiv@gmail.com"  # troque por um usuário que já exista

def main():
    db = SessionLocal()

    usuario = db.query(Usuario).filter(Usuario.email == EMAIL_USUARIO).first()
    if not usuario:
        print("Usuário não encontrado, crie o usuário no sistema primeiro.")
        return

    token = TokenAtivacao.gerar_token(
        usuario_id=usuario.id,
        plano="consultoria_full",
        dias_validade=365,
    )

    db.add(token)
    db.commit()
    db.refresh(token)

    print("TOKEN GERADO:")
    print(token.token)
    print("Expira em:", token.expira_em)

    db.close()

if __name__ == "__main__":
    main()
