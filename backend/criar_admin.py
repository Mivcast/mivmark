from backend.database import SessionLocal
from backend.models import Usuario
from datetime import datetime
from passlib.hash import bcrypt

db = SessionLocal()

email = "admin@mivmark.com"
senha = "123456"
nome = "Admin"
tipo = "admin"

# Verifica se já existe
usuario = db.query(Usuario).filter(Usuario.email == email).first()
if usuario:
    print("Usuário admin já existe.")
else:
    novo = Usuario(
        nome=nome,
        email=email,
        senha_hash=bcrypt.hash(senha),
        tipo_usuario=tipo,
        plano_atual="premium",
        data_criacao=datetime.utcnow()
    )
    db.add(novo)
    db.commit()
    print("Usuário admin criado com sucesso.")
