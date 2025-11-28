# backend/api/usuario.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Usuario, Diagnostico
from backend.models.tokens import TokenAtivacao
from backend.api.auth import get_usuario_logado
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter(prefix="/usuario", tags=["Usuário"])


# ============================================================
# 🚀 CADASTRO GRATUITO – com teste de 7 dias do Plano Profissional
# ============================================================

class CadastroRequest(BaseModel):
    nome: str
    email: str
    senha: str


@router.post("/cadastro/gratuito")
def cadastro_gratuito(dados: CadastroRequest, db: Session = Depends(get_db)):
    """
    Cria um usuário gratuito com teste de 7 dias do plano Profissional.
    Após 7 dias, o backend (auth) derruba automaticamente para plano 'Gratuito'.
    """

    # Verificar se já existe
    existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    agora = datetime.utcnow()

    # Senha será hasheada pelo auth no login, então aqui salva direto
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=dados.senha,  # ⚠ importante: login vai hashear ao validar
        tipo_usuario="cliente",

        # 🔥 TESTE LIBERADO – 7 dias de acesso ao Plano Profissional
        plano_atual="Profissional",
        plano_expira_em=agora + timedelta(days=7),

        data_criacao=agora,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return {
        "mensagem": "Cadastro criado! Você ganhou 7 dias do plano Profissional.",
        "usuario_id": usuario.id,
        "plano_atual": usuario.plano_atual,
        "plano_expira_em": usuario.plano_expira_em,
    }


# ============================================================
# 🧠 SALVAR DIAGNÓSTICO DE SAÚDE
# ============================================================

@router.put("/nota_saude")
def salvar_diagnostico(
    dados: dict,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    usuario = db.merge(usuario)

    nota = dados.get("nota")
    respostas = dados.get("respostas")

    if nota is not None:
        usuario.nota_saude = f"{nota:.2f}%"
    if respostas is not None:
        usuario.respostas_saude = respostas

    db.commit()
    db.refresh(usuario)

    return {"mensagem": "Diagnóstico salvo com sucesso"}


@router.get("/diagnosticos")
def listar_diagnosticos(
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    diagnosticos = (
        db.query(Diagnostico)
        .filter(Diagnostico.usuario_id == usuario.id)
        .order_by(Diagnostico.data_avaliacao.desc())
        .all()
    )

    return [
        {
            "id": d.id,
            "data_avaliacao": d.data_avaliacao.isoformat() if d.data_avaliacao else None,
            "nota_geral": d.nota_geral,
            "respostas": d.respostas
        }
        for d in diagnosticos
    ]


# ============================================================
# 🔑 ATIVAÇÃO DE TOKEN – Planos pagos
# ============================================================

class TokenAtivacaoRequest(BaseModel):
    token: str


@router.post("/ativar_token")
def ativar_token(
    dados: TokenAtivacaoRequest,
    usuario: Usuario = Depends(get_usuario_logado),
    db: Session = Depends(get_db),
):
    token_str = (dados.token or "").strip()

    if not token_str:
        raise HTTPException(status_code=400, detail="Token não informado.")

    token = db.query(TokenAtivacao).filter(TokenAtivacao.token == token_str).first()

    if not token:
        raise HTTPException(status_code=400, detail="Token inválido.")

    if not token.ativo:
        raise HTTPException(status_code=400, detail="Token já foi utilizado.")

    # Expirado?
    if token.expira_em and token.expira_em < datetime.utcnow():
        token.ativo = False
        db.commit()
        raise HTTPException(status_code=400, detail="Token expirado.")

    # Vinculado a outro usuário?
    if token.usuario_id and token.usuario_id != usuario.id:
        raise HTTPException(
            status_code=400,
            detail="Este token já foi vinculado a outra conta.",
        )

    # Associar ao usuário atual (se ainda não tiver)
    if not token.usuario_id:
        token.usuario_id = usuario.id

    # Plano definido no token ou padrão 'Profissional'
    plano = token.plano or "Profissional"
    usuario.plano_atual = plano

    # Expiração existente ou 1 ano
    if token.expira_em:
        usuario.plano_expira_em = token.expira_em
    else:
        usuario.plano_expira_em = datetime.utcnow() + timedelta(days=365)
        token.expira_em = usuario.plano_expira_em

    token.ativo = False

    db.commit()
    db.refresh(usuario)
    db.refresh(token)

    return {
        "mensagem": "Plano ativado com sucesso!",
        "plano": usuario.plano_atual,
        "expira_em": usuario.plano_expira_em.isoformat() if usuario.plano_expira_em else None,
    }
