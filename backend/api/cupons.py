# backend/api/cupons.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import date

from backend.database import get_db
from backend.api.auth import get_usuario_logado
from backend.models import Usuario
from backend.models.cupom import CupomDesconto
from backend.models.planos import Plano

router = APIRouter(prefix="/cupons", tags=["Cupons"])


# -------------------------
# Schemas
# -------------------------
class CupomCreate(BaseModel):
    codigo: str
    descricao: Optional[str] = None
    desconto_percent: float

    # "curso" | "plano" | "aplicativo"
    escopo: str

    # alvo do cupom (opcionais, dependendo do escopo)
    curso_id: Optional[int] = None
    aplicativo_id: Optional[int] = None

    # FRONT pode mandar plano_id (0 = todos) => vamos converter para plano_nome
    plano_id: Optional[int] = None

    valido_ate: Optional[date] = None  # None = sem validade
    ativo: bool = True


class CupomUpdate(BaseModel):
    descricao: Optional[str] = None
    desconto_percent: Optional[float] = None
    escopo: Optional[str] = None

    curso_id: Optional[int] = None
    aplicativo_id: Optional[int] = None
    plano_id: Optional[int] = None

    valido_ate: Optional[date] = None
    ativo: Optional[bool] = None


class CupomOut(BaseModel):
    id: int
    codigo: str
    descricao: Optional[str]
    desconto_percent: Optional[float]
    escopo: Optional[str]

    curso_id: Optional[int]
    aplicativo_id: Optional[int]
    plano_nome: Optional[str]

    valido_ate: Optional[date]  # ✅ alinhado com payload/model
    ativo: bool

    class Config:
        from_attributes = True


# -------------------------
# Helpers
# -------------------------
def _codigo_normalizado(c: str) -> str:
    return (c or "").strip().lower()


def _validar_escopo(escopo: str) -> str:
    escopo = (escopo or "").strip().lower()
    if escopo not in ("curso", "plano", "aplicativo"):
        raise HTTPException(status_code=400, detail="escopo deve ser 'curso', 'plano' ou 'aplicativo'")
    return escopo


def _so_admin(usuario: Usuario):
    if getattr(usuario, "is_admin", False) is True:
        return
    if getattr(usuario, "tipo_usuario", "") == "admin":
        return
    raise HTTPException(status_code=403, detail="Apenas admin pode gerenciar cupons")


def _resolver_plano_nome(db: Session, plano_id: Optional[int]) -> str:
    # 0 ou None = todos
    if not plano_id or int(plano_id) == 0:
        return "todos"

    plano = db.query(Plano).filter(Plano.id == int(plano_id)).first()
    if not plano:
        raise HTTPException(status_code=400, detail="Plano não encontrado para vincular ao cupom.")

    # precisa ser o NOME do plano
    return (plano.nome or "").strip()


def _validar_valido_ate(valido_ate: Optional[date]):
    if valido_ate and valido_ate < date.today():
        raise HTTPException(status_code=400, detail="valido_ate não pode estar no passado.")


# -------------------------
# CRUD
# -------------------------
@router.post("", response_model=CupomOut)
def criar_cupom(
    payload: CupomCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    codigo = _codigo_normalizado(payload.codigo)
    if not codigo:
        raise HTTPException(status_code=400, detail="Código do cupom é obrigatório.")

    # Evita duplicidade global (mesmo código não pode existir em nenhum escopo)
    ja_existe = db.query(CupomDesconto).filter(CupomDesconto.codigo == codigo).first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Já existe um cupom com esse código.")

    escopo = _validar_escopo(payload.escopo)
    _validar_valido_ate(payload.valido_ate)

    # Normaliza alvo conforme escopo
    curso_id = None
    aplicativo_id = None
    plano_nome = None

    if escopo == "plano":
        # ✅ CORRETO: (db, plano_id)
        plano_nome = _resolver_plano_nome(db, payload.plano_id)
    elif escopo == "curso":
        curso_id = payload.curso_id  # None => vale para todos os cursos
    elif escopo == "aplicativo":
        aplicativo_id = payload.aplicativo_id  # None => vale para todos os apps

    # Como seu front trabalha com "desconto_percent", vamos gravar como cupom percentual:
    tipo_valor = "percent"
    valor = float(payload.desconto_percent or 0)

    cupom = CupomDesconto(
        codigo=codigo,
        descricao=payload.descricao,
        desconto_percent=payload.desconto_percent,

        escopo=escopo,
        curso_id=curso_id,
        aplicativo_id=aplicativo_id,
        plano_nome=plano_nome,
        valido_ate=payload.valido_ate,
        ativo=payload.ativo,

        # campos NOT NULL no seu banco
        tipo_valor=tipo_valor,
        valor=valor,
        tipo_aplicacao="desconto",
        usos_realizados=0,
    )

    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return cupom


@router.get("", response_model=List[CupomOut])
def listar_cupons(escopo: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CupomDesconto)
    if escopo:
        q = q.filter(CupomDesconto.escopo == escopo.strip().lower())
    return q.order_by(CupomDesconto.id.desc()).all()


@router.put("/{cupom_id}", response_model=CupomOut)
def editar_cupom(
    cupom_id: int,
    payload: CupomUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    cupom = db.query(CupomDesconto).filter(CupomDesconto.id == cupom_id).first()
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")

    if payload.escopo is not None:
        escopo = _validar_escopo(payload.escopo)
        cupom.escopo = escopo

        # ao trocar escopo, limpa vínculos conflitantes
        if escopo == "plano":
            cupom.curso_id = None
            cupom.aplicativo_id = None
            # ✅ CORRETO: (db, plano_id)
            cupom.plano_nome = _resolver_plano_nome(db, payload.plano_id) if payload.plano_id is not None else "todos"
        elif escopo == "curso":
            cupom.plano_nome = None
            cupom.aplicativo_id = None
            cupom.curso_id = payload.curso_id
        elif escopo == "aplicativo":
            cupom.plano_nome = None
            cupom.curso_id = None
            cupom.aplicativo_id = payload.aplicativo_id

    if payload.descricao is not None:
        cupom.descricao = payload.descricao
    if payload.desconto_percent is not None:
        cupom.desconto_percent = payload.desconto_percent
        # mantém coerente com valor/tipo_valor
        cupom.tipo_valor = "percent"
        cupom.valor = float(payload.desconto_percent or 0)
    if payload.valido_ate is not None:
        _validar_valido_ate(payload.valido_ate)
        cupom.valido_ate = payload.valido_ate
    if payload.ativo is not None:
        cupom.ativo = payload.ativo

    # Atualiza alvo (sem trocar escopo)
    if payload.escopo is None:
        if cupom.escopo == "plano" and payload.plano_id is not None:
            # ✅ CORRETO: (db, plano_id)
            cupom.plano_nome = _resolver_plano_nome(db, payload.plano_id)
        if cupom.escopo == "curso" and payload.curso_id is not None:
            cupom.curso_id = payload.curso_id
        if cupom.escopo == "aplicativo" and payload.aplicativo_id is not None:
            cupom.aplicativo_id = payload.aplicativo_id

    db.commit()
    db.refresh(cupom)
    return cupom


@router.delete("/{cupom_id}")
def excluir_cupom(
    cupom_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    _so_admin(usuario)

    cupom = db.query(CupomDesconto).filter(CupomDesconto.id == cupom_id).first()
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")

    db.delete(cupom)
    db.commit()
    return {"ok": True}
