# backend/api/auth.py

from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, sessionmaker
from backend.database import engine
from backend.models import Usuario
from backend.models.tokens import TokenAtivacao
from sqlalchemy import select
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import secrets

# -------------------------------------------------
# Configurações gerais
# -------------------------------------------------

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SECRET_KEY = "chave-super-secreta-do-mark"
ALGORITHM = "HS256"
TEMPO_EXPIRACAO = 60 * 24  # 24 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# -------------------------------------------------
# Schemas
# -------------------------------------------------

class CadastroSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    token_ativacao: str  # usado para planos pagos


class CadastroGratuitoSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str


# -------------------------------------------------
# Cadastro com TOKEN (planos pagos)
# -------------------------------------------------

@router.post("/cadastro")
def cadastrar_usuario(dados: CadastroSchema):
    db: Session = SessionLocal()

    # Verifica se o e-mail já existe
    if db.execute(select(Usuario).where(Usuario.email == dados.email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    # Verifica se o token existe e está ativo
    token_db = db.execute(
        select(TokenAtivacao).where(TokenAtivacao.token == dados.token_ativacao)
    ).scalar_one_or_none()

    if not token_db or not token_db.ativo:
        raise HTTPException(status_code=400, detail="Token de ativação inválido ou já utilizado.")

    # Cria novo usuário
    senha_hash = pwd_context.hash(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=senha_hash,
        data_criacao=datetime.utcnow(),
        plano_atual="ativo"  # depois poderá ser ajustado pelo token/planos
    )

    db.add(novo_usuario)

    # Marca o token como usado
    token_db.ativo = False
    db.commit()
    db.refresh(novo_usuario)

    return {"mensagem": "Usuário cadastrado com sucesso", "id": novo_usuario.id}


# -------------------------------------------------
# Login
# -------------------------------------------------

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db: Session = SessionLocal()
    usuario = db.execute(
        select(Usuario).where(Usuario.email == form_data.username)
    ).scalar_one_or_none()

    # 1️⃣ E-mail não encontrado
    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="EMAIL_NAO_ENCONTRADO"
        )

    # 2️⃣ Senha incorreta
    if not pwd_context.verify(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="SENHA_INCORRETA"
        )

    # 3️⃣ Verifica se o plano do usuário expirou
    if (
        usuario.tipo_usuario != "admin"
        and usuario.plano_expira_em is not None
        and datetime.utcnow() > usuario.plano_expira_em
    ):
        usuario.plano_atual = "Gratuito"
        db.commit()
        db.refresh(usuario)

    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "email": usuario.email,
            "exp": datetime.utcnow() + timedelta(minutes=TEMPO_EXPIRACAO),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": usuario.email,
        "nome": usuario.nome,
        "tipo_usuario": usuario.tipo_usuario,
        "plano_atual": usuario.plano_atual
        or ("Administrador" if usuario.tipo_usuario == "admin" else "Gratuito"),
    }




# -------------------------------------------------
# Helpers de autenticação
# -------------------------------------------------

def get_current_user(token: str = Depends(oauth2_scheme)) -> Usuario:
    """
    Usado em rotas que chamam diretamente get_current_user.
    Faz também a verificação de expiração de plano.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    db: Session = SessionLocal()
    usuario = db.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    # 🔥 Verifica expiração de plano (teste ou plano pago com data)
    if (
        usuario.tipo_usuario != "admin"
        and usuario.plano_expira_em is not None
        and datetime.utcnow() > usuario.plano_expira_em
    ):
        usuario.plano_atual = "Gratuito"
        db.commit()
        db.refresh(usuario)

    return usuario


def get_usuario_logado(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Alias usado em outros módulos (empresa, usuario, etc.).
    Também faz a verificação de expiração de plano.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    usuario = db.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    # 🔥 Verifica expiração de plano
    if (
        usuario.tipo_usuario != "admin"
        and usuario.plano_expira_em is not None
        and datetime.utcnow() > usuario.plano_expira_em
    ):
        usuario.plano_atual = "Gratuito"
        db.commit()
        db.refresh(usuario)

    return usuario


# -------------------------------------------------
# Minha conta
# -------------------------------------------------

@router.get("/minha-conta")
def minha_conta(usuario: Usuario = Depends(get_current_user)):
    """
    Retorna dados básicos do usuário logado e da empresa.
    Inclui plano_atual e plano_expira_em para o frontend saber do teste.
    """
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "plano_atual": usuario.plano_atual,
        "plano_expira_em": usuario.plano_expira_em,
        "tipo_usuario": usuario.tipo_usuario,
        "is_admin": usuario.tipo_usuario == "admin",
        "data_criacao": usuario.data_criacao,
        "nota_saude": usuario.nota_saude,
        "respostas_saude": usuario.respostas_saude,
        "logo_url": usuario.empresa.logo_url if usuario.empresa else None,
        "empresa": {
            "nome_empresa": usuario.empresa.nome_empresa,
            "descricao": usuario.empresa.descricao,
            "nicho": usuario.empresa.nicho,
            "funcionarios": usuario.empresa.funcionarios,
            "produtos": usuario.empresa.produtos,
            "redes_sociais": usuario.empresa.redes_sociais,
            "informacoes_adicionais": usuario.empresa.informacoes_adicionais,
        }
        if usuario.empresa
        else None,
    }


# -------------------------------------------------
# Cadastro GRATUITO – teste de 7 dias (Plano Profissional)
# -------------------------------------------------

@router.post("/cadastro/gratuito")
def cadastrar_usuario_gratuito(dados: CadastroGratuitoSchema):
    """
    Cadastro sem token.
    Ganha 7 dias de acesso ao plano Profissional.
    Depois disso, será rebaixado automaticamente para 'Gratuito'.
    """
    db: Session = SessionLocal()

    if db.execute(select(Usuario).where(Usuario.email == dados.email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    senha_hash = pwd_context.hash(dados.senha)
    agora = datetime.utcnow()

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=senha_hash,
        data_criacao=agora,
        tipo_usuario="cliente",
        plano_atual="Profissional",                 # 🔥 teste com plano profissional
        plano_expira_em=agora + timedelta(days=7),  # 🔥 expira em 7 dias
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return {
        "mensagem": "Usuário gratuito criado com sucesso. Você ganhou 7 dias do plano Profissional.",
        "id": novo_usuario.id,
        "plano_atual": novo_usuario.plano_atual,
        "plano_expira_em": novo_usuario.plano_expira_em,
    }


# -------------------------------------------------
# Rotas ADMIN – tokens e lista de usuários
# -------------------------------------------------

@router.post("/admin/gerar_token")
def gerar_token_admin(senha_admin: str):
    if senha_admin != "123456":
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    db: Session = SessionLocal()
    token_gerado = secrets.token_hex(8)  # 16 caracteres

    novo_token = TokenAtivacao(token=token_gerado)
    db.add(novo_token)
    db.commit()

    return {"token_ativacao": token_gerado}


@router.get("/admin/listar_tokens")
def listar_tokens(senha_admin: str):
    if senha_admin != "123456":
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    db: Session = SessionLocal()
    tokens = db.query(TokenAtivacao).order_by(TokenAtivacao.id.desc()).all()

    return [
        {
            "token": t.token,
            "ativo": t.ativo,
            "data_criacao": t.data_criacao.isoformat() if t.data_criacao else None,
        }
        for t in tokens
    ]


@router.get("/admin/usuarios")
def listar_usuarios(senha_admin: str):
    if senha_admin != "123456":
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    db: Session = SessionLocal()
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).all()

    return [
        {
            "nome": u.nome,
            "email": u.email,
            "tipo_usuario": u.tipo_usuario,
            "plano_atual": u.plano_atual,
            "plano_expira_em": u.plano_expira_em,
            "data_criacao": u.data_criacao.isoformat() if u.data_criacao else None,
        }
        for u in usuarios
    ]
