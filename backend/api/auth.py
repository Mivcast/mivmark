from fastapi import APIRouter, HTTPException, Depends
from database import get_db  # Importar get_db aqui
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, sessionmaker
from database import engine
from models import Usuario
from sqlalchemy import select
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models.tokens import TokenAtivacao
from models.demo import CadastroDemo

import secrets

# Inicializações
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SECRET_KEY = "chave-super-secreta-do-mark"
ALGORITHM = "HS256"
TEMPO_EXPIRACAO = 60 * 24  # 24 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Schema de Demonstração do sistema para usuarios desconhecidos
class CadastroDemoSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    setor: str

# Schema de entrada
class CadastroSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    token_ativacao: str  # novo campo obrigatório

# Rota de cadastro
@router.post("/cadastro")
def cadastrar_usuario(dados: CadastroSchema):
    db: Session = SessionLocal()

    # Verifica se o e-mail já existe
    if db.execute(select(Usuario).where(Usuario.email == dados.email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    # Verifica se o token existe e está ativo
    token_db = db.execute(select(TokenAtivacao).where(TokenAtivacao.token == dados.token_ativacao)).scalar_one_or_none()
    if not token_db or not token_db.ativo:
        raise HTTPException(status_code=400, detail="Token de ativação inválido ou já utilizado.")

    # Cria novo usuário
    senha_hash = pwd_context.hash(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=senha_hash,
        data_criacao=datetime.utcnow(),
        plano_atual="ativo"
    )

    db.add(novo_usuario)

    # Marca o token como usado
    token_db.ativo = False
    db.commit()
    db.refresh(novo_usuario)

    return {"mensagem": "Usuário cadastrado com sucesso", "id": novo_usuario.id}

# Rota de login
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    usuario = db.execute(select(Usuario).where(Usuario.email == form_data.username)).scalar_one_or_none()

    if not usuario or not pwd_context.verify(form_data.password, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Credenciais inválidas.")

    token = jwt.encode({
        "sub": str(usuario.id),
        "email": usuario.email,
        "exp": datetime.utcnow() + timedelta(minutes=TEMPO_EXPIRACAO)
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {
    "access_token": token,
    "token_type": "bearer",
    "email": usuario.email,
    "nome": usuario.nome,
    "tipo_usuario": usuario.tipo_usuario,
    "plano_atual": usuario.plano_atual or ("Administrador" if usuario.tipo_usuario == "admin" else "Gratuito")
    }

# Verifica o token e retorna usuário
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))

        db = SessionLocal()
        usuario = db.get(Usuario, user_id)
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuário não encontrado.")
        return usuario

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

# Alias para o nome esperado no código: get_usuario_logado
def get_usuario_logado(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    usuario = db.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return usuario

# Rota protegida
@router.get("/minha-conta")
def minha_conta(usuario: Usuario = Depends(get_current_user)):
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "plano_atual": usuario.plano_atual,
        "tipo_usuario": usuario.tipo_usuario,
        "is_admin": usuario.tipo_usuario == "admin",  # ← ESSENCIAL
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
        } if usuario.empresa else None
    }


@router.post("/cadastro/demo")
def cadastrar_demo(dados: CadastroDemoSchema):
    db: Session = SessionLocal()

    # Verifica se já existe usuário com o e-mail
    if db.execute(select(Usuario).where(Usuario.email == dados.email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    # Verifica se já usou demo para o setor
    ja_usou = db.execute(
        select(CadastroDemo).where(
            CadastroDemo.email == dados.email,
            CadastroDemo.setor == dados.setor
        )
    ).scalar_one_or_none()

    if ja_usou:
        raise HTTPException(status_code=400, detail="Você já usou o acesso demo para este setor.")

    # Cria novo usuário com plano demo
    senha_hash = pwd_context.hash(dados.senha)
    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=senha_hash,
        plano_atual="demo",
        data_criacao=datetime.utcnow()
    )

    db.add(novo_usuario)

    # Registra o uso do demo
    registro_demo = CadastroDemo(
        email=dados.email,
        setor=dados.setor
    )
    db.add(registro_demo)

    db.commit()
    db.refresh(novo_usuario)

    return {"mensagem": "Acesso demo criado com sucesso", "id": novo_usuario.id}


# Novo cadastro gratuito sem token
class CadastroGratuitoSchema(BaseModel):
    nome: str
    email: EmailStr
    senha: str

@router.post("/cadastro/gratuito")
def cadastrar_usuario_gratuito(dados: CadastroGratuitoSchema):
    db: Session = SessionLocal()

    if db.execute(select(Usuario).where(Usuario.email == dados.email)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    senha_hash = pwd_context.hash(dados.senha)

    novo_usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=senha_hash,
        data_criacao=datetime.utcnow(),
        plano_atual="Gratuito",
        tipo_usuario="comum"
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return {"mensagem": "Usuário gratuito criado com sucesso", "id": novo_usuario.id}



@router.post("/admin/gerar_token")
def gerar_token_admin(senha_admin: str):
    if senha_admin != "123456":
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    db: Session = SessionLocal()
    token_gerado = secrets.token_hex(8)  # Gera um token aleatório de 16 caracteres

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

    return [{
        "token": t.token,
        "ativo": t.ativo,
        "data_criacao": t.data_criacao.isoformat() if t.data_criacao else None
    } for t in tokens]

@router.get("/admin/usuarios")
def listar_usuarios(senha_admin: str):
    if senha_admin != "123456":
        raise HTTPException(status_code=401, detail="Acesso não autorizado.")

    db: Session = SessionLocal()
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).all()

    return [{
        "nome": u.nome,
        "email": u.email,
        "tipo_usuario": u.tipo_usuario,
        "plano_atual": u.plano_atual,
        "data_criacao": u.data_criacao.isoformat() if u.data_criacao else None
    } for u in usuarios]
