# backend/api/conta.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models import Usuario
from backend.api.auth import get_usuario_logado  # usa seu JWT atual

from datetime import datetime, timedelta
import secrets
from backend.models.senha_reset import SenhaResetToken

# Se no seu auth.py já existir pwd_context, vamos reutilizar.
# Caso não exista, vamos criar aqui (mais seguro deixar local).
try:
    from backend.api.auth import pwd_context  # type: ignore
except Exception:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/conta", tags=["Minha Conta"])


class MeResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    plano: Optional[str] = None
    tipo_usuario: Optional[str] = None
    status: Optional[str] = None


class UpdateEmailRequest(BaseModel):
    email_novo: EmailStr


class UpdateSenhaRequest(BaseModel):
    senha_atual: str
    senha_nova: str


@router.get("/me", response_model=MeResponse)
def me(
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    # Ajuste de campos conforme seu model Usuario
    return MeResponse(
        id=usuario_logado.id,
        nome=getattr(usuario_logado, "nome", "") or "",
        email=usuario_logado.email,
        plano=getattr(usuario_logado, "plano", None),
        tipo_usuario=getattr(usuario_logado, "tipo_usuario", None),
        status=getattr(usuario_logado, "status", None),
    )


@router.put("/me/email")
def atualizar_email(
    payload: UpdateEmailRequest,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    email_novo = payload.email_novo.strip().lower()

    # Se não mudou, retorna ok sem fazer nada
    if email_novo == (usuario_logado.email or "").strip().lower():
        return {"ok": True, "msg": "E-mail já está atualizado."}

    # Verifica se já existe
    existe = db.query(Usuario).filter(Usuario.email == email_novo).first()
    if existe:
        raise HTTPException(status_code=400, detail="Este e-mail já está em uso.")

    usuario_logado.email = email_novo
    db.add(usuario_logado)
    db.commit()
    db.refresh(usuario_logado)

    return {"ok": True, "msg": "E-mail atualizado com sucesso.", "email": usuario_logado.email}


@router.put("/me/senha")
def atualizar_senha(
    payload: UpdateSenhaRequest,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    senha_atual = payload.senha_atual or ""
    senha_nova = payload.senha_nova or ""

    if len(senha_nova) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres.")

    # Campos comuns do hash no Usuario:
    # - senha_hash (muito comum)
    # - hashed_password (às vezes)
    senha_hash = getattr(usuario_logado, "senha_hash", None) or getattr(usuario_logado, "hashed_password", None)

    if not senha_hash:
        raise HTTPException(status_code=500, detail="Usuário sem hash de senha cadastrado (configuração inválida).")

    # Confere senha atual
    if not pwd_context.verify(senha_atual, senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    novo_hash = pwd_context.hash(senha_nova)

    # Atualiza no campo correto
    if hasattr(usuario_logado, "senha_hash"):
        usuario_logado.senha_hash = novo_hash
    else:
        usuario_logado.hashed_password = novo_hash

    db.add(usuario_logado)
    db.commit()

    return {"ok": True, "msg": "Senha atualizada com sucesso."}


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    email: EmailStr
    codigo: str
    senha_nova: str


def _gerar_codigo_6_digitos() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _enviar_email_reset(email_destino: str, codigo: str):
    assunto = "MivMark - Código para redefinir sua senha"
    corpo = (
        "Olá!\n\n"
        "Recebemos um pedido para redefinir sua senha no MivMark.\n\n"
        f"Seu código é: {codigo}\n\n"
        "⏱️ Este código expira em 15 minutos.\n\n"
        "Se você não solicitou essa alteração, ignore este e-mail.\n\n"
        "Equipe MivCast"
    )

    try:
        from backend.utils.email_utils import enviar_email

        # 🔹 chamada POSICIONAL (sem keyword)
        enviar_email(email_destino, assunto, corpo)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar e-mail de redefinição de senha: {e}"
        )



@router.post("/esqueci-senha")
def esqueci_senha(payload: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    # Importante: não revelar se o e-mail existe (segurança).
    # Então sempre respondemos "ok", mas só enviamos se existir.
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"ok": True, "msg": "Se este e-mail estiver cadastrado, você receberá um código em instantes."}

    # Gera código e salva hash
    codigo = _gerar_codigo_6_digitos()
    codigo_hash = pwd_context.hash(codigo)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    token = SenhaResetToken(
        email=email,
        codigo_hash=codigo_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(token)
    db.commit()

    # Envia e-mail
    _enviar_email_reset(email, codigo)

    return {"ok": True, "msg": "Se este e-mail estiver cadastrado, você receberá um código em instantes."}


@router.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    codigo = (payload.codigo or "").strip()
    senha_nova = payload.senha_nova or ""

    if len(senha_nova) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres.")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        # Mantém resposta genérica (não revelar)
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    # Busca token mais recente não usado
    token = (
        db.query(SenhaResetToken)
        .filter(SenhaResetToken.email == email, SenhaResetToken.used == False)  # noqa: E712
        .order_by(SenhaResetToken.created_at.desc())
        .first()
    )

    if not token:
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    if token.expires_at < datetime.utcnow():
        token.used = True
        db.add(token)
        db.commit()
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    # Valida código
    if not pwd_context.verify(codigo, token.codigo_hash):
        raise HTTPException(status_code=400, detail="Código inválido ou expirado.")

    # Atualiza senha do usuário
    novo_hash = pwd_context.hash(senha_nova)

    if hasattr(usuario, "senha_hash"):
        usuario.senha_hash = novo_hash
    elif hasattr(usuario, "hashed_password"):
        usuario.hashed_password = novo_hash
    else:
        raise HTTPException(status_code=500, detail="Campo de senha não encontrado no model Usuario.")

    # Invalida token
    token.used = True

    db.add(usuario)
    db.add(token)
    db.commit()

    return {"ok": True, "msg": "Senha redefinida com sucesso. Agora você já pode fazer login."}

