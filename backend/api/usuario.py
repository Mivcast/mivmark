# backend/api/usuario.py

from datetime import datetime, timedelta
import secrets
import string


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from passlib.context import CryptContext  # 🔐 para hash de senha

from backend.database import get_db
from backend.models import Usuario, Diagnostico
from backend.models.tokens import TokenAtivacao
from backend.api.auth import get_usuario_logado
from backend.utils.email_utils import enviar_email

router = APIRouter(prefix="/usuario", tags=["Usuários"])

# =========================
# CONTEXTO DE SENHA
# =========================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash seguro da senha."""
    return pwd_context.hash(senha)


# =========================
# MODELOS DE DADOS
# =========================

class CadastroGratuito(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class DiagnosticoRequest(BaseModel):
    nota_saude: float
    respostas_json: dict


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr


# =========================
# FUNÇÕES AUXILIARES
# =========================

def gerar_senha_temporaria(tamanho: int = 8) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


# =========================
# ROTAS
# =========================

@router.post("/cadastro-gratuito")
def cadastro_gratuito(dados: CadastroGratuito, db: Session = Depends(get_db)):
    """
    Cria usuário e libera 7 dias de acesso ao plano Profissional.
    """

    usuario_existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Já existe um usuário com esse e-mail.")

    agora = datetime.utcnow()

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        # 🔐 agora salvando a senha já com HASH bcrypt
        senha_hash=hash_senha(dados.senha),
        plano_atual="Profissional",
        plano_expira_em=agora + timedelta(days=7),
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    # E-mail de boas-vindas + teste de 7 dias
    assunto = "Bem-vindo ao MivMark 🎯 – 7 dias de acesso Profissional liberados"
    corpo_html = f"""
    <p>Olá, <strong>{usuario.nome}</strong>!</p>

    <p>Seu cadastro no <strong>MivMark</strong> foi realizado com sucesso. 🙌</p>

    <p>Você ganhou <strong>7 dias de acesso ao plano Profissional</strong>
    para conhecer praticamente todas as funções do sistema.</p>

    <p>Dados de acesso:</p>
    <ul>
        <li><strong>E-mail:</strong> {usuario.email}</li>
        <li><strong>Senha:</strong> {dados.senha}</li>
    </ul>

    <p>Após esses 7 dias, você pode escolher o plano que fizer mais sentido para o seu momento.</p>

    <p>
        Acesse o sistema pelo link:<br>
        <a href="https://mivmark-frontend.onrender.com" target="_blank">
            https://mivmark-frontend.onrender.com
        </a>
    </p>

    <p>Qualquer dúvida, é só responder este e-mail.<br>
    <strong>Matheus – MivCast / MivMark</strong></p>
    """

    try:
        enviar_email(usuario.email, assunto, corpo_html)
    except Exception as e:
        print(f"[CADASTRO] Erro ao enviar e-mail de boas-vindas: {e}")

    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "plano_atual": usuario.plano_atual,
        "plano_expira_em": usuario.plano_expira_em,
    }



@router.post("/diagnostico")
def salvar_diagnostico(
    dados: DiagnosticoRequest,
    usuario=Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """
    Salva ou atualiza o diagnóstico de saúde da empresa do usuário logado.
    """

    diagnostico = (
        db.query(Diagnostico)
        .filter(Diagnostico.usuario_id == usuario.id)
        .first()
    )

    if diagnostico:
        diagnostico.nota_saude = dados.nota_saude
        diagnostico.respostas_json = dados.respostas_json
        diagnostico.atualizado_em = datetime.utcnow()
    else:
        diagnostico = Diagnostico(
            usuario_id=usuario.id,
            nota_saude=dados.nota_saude,
            respostas_json=dados.respostas_json,
            criado_em=datetime.utcnow(),
        )
        db.add(diagnostico)

    db.commit()
    db.refresh(diagnostico)

    return {
        "id": diagnostico.id,
        "nota_saude": diagnostico.nota_saude,
        "respostas_json": diagnostico.respostas_json,
    }


@router.get("/diagnostico")
def obter_diagnostico(
    usuario=Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    """
    Retorna o diagnóstico salvo do usuário logado (se existir).
    """

    diagnostico = (
        db.query(Diagnostico)
        .filter(Diagnostico.usuario_id == usuario.id)
        .first()
    )

    if not diagnostico:
        return None

    return {
        "id": diagnostico.id,
        "nota_saude": diagnostico.nota_saude,
        "respostas_json": diagnostico.respostas_json,
    }


@router.post("/ativar_token")
def ativar_token(token: str, db: Session = Depends(get_db)):
    """
    Ativa um token de plano pago e vincula ao usuário.
    """

    token_registro = (
        db.query(TokenAtivacao)
        .filter(TokenAtivacao.token == token, TokenAtivacao.usado_em == None)
        .first()
    )

    if not token_registro:
        raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")

    if token_registro.expira_em and token_registro.expira_em < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado.")

    usuario = db.query(Usuario).filter(Usuario.email == token_registro.email_cliente).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado para este token.")

    usuario.plano_atual = token_registro.plano_nome
    usuario.plano_expira_em = datetime.utcnow() + timedelta(days=30)

    token_registro.usado_em = datetime.utcnow()

    db.commit()
    db.refresh(usuario)

    return {
        "mensagem": "Plano ativado com sucesso.",
        "plano_atual": usuario.plano_atual,
        "plano_expira_em": usuario.plano_expira_em,
    }


@router.post("/esqueci-senha")
def esqueci_senha(dados: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    """
    Gera uma nova senha temporária, SALVA com hash e envia por e-mail.
    """

    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Nenhum usuário encontrado com esse e-mail.")

    nova_senha = gerar_senha_temporaria(10)

    # 🔐 salva a senha temporária já com hash, compatível com o /login
    usuario.senha_hash = hash_senha(nova_senha)
    db.commit()
    db.refresh(usuario)

    assunto = "MivMark – Nova senha de acesso"
    corpo_html = f"""
    <p>Olá, <strong>{usuario.nome}</strong>!</p>

    <p>Você solicitou a redefinição da sua senha no <strong>MivMark</strong>.</p>

    <p>Sua nova senha temporária é:</p>
    <p style="font-size: 18px;">
        <strong>{nova_senha}</strong>
    </p>

    <p>
        Use essa senha para entrar no sistema e, depois, altere-a no seu cadastro
        para algo fácil de lembrar e seguro.
    </p>

    <p>
        Acesse:<br>
        <a href="https://mivmark-frontend.onrender.com" target="_blank">
            https://mivmark-frontend.onrender.com
        </a>
    </p>
    """

    try:
        enviar_email(usuario.email, assunto, corpo_html)
    except Exception as e:
        print(f"[ESQUECI SENHA] Erro ao enviar e-mail: {e}")
        raise HTTPException(status_code=500, detail="Erro ao enviar e-mail. Tente novamente mais tarde.")

    return {"detail": "Nova senha enviada para o seu e-mail."}
