# backend/api/cupons.py
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.cupons import CupomDesconto, CupomSchema, CupomCreate

router = APIRouter(prefix="/cupons", tags=["Cupons"])


@router.get("/", response_model=list[CupomSchema])
def listar_cupons(db: Session = Depends(get_db)):
    return db.query(CupomDesconto).all()


@router.post("/", response_model=CupomSchema)
def criar_cupom(cupom: CupomCreate, db: Session = Depends(get_db)):
    # Verifica se já existe código igual
    existente = db.query(CupomDesconto).filter(
        CupomDesconto.codigo == cupom.codigo
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Código de cupom já existe.")

    novo = CupomDesconto(**cupom.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.put("/{cupom_id}", response_model=CupomSchema)
def atualizar_cupom(cupom_id: int, cupom: CupomCreate, db: Session = Depends(get_db)):
    db_cupom = db.query(CupomDesconto).filter(CupomDesconto.id == cupom_id).first()
    if not db_cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado.")

    for campo, valor in cupom.dict().items():
        setattr(db_cupom, campo, valor)

    db.commit()
    db.refresh(db_cupom)
    return db_cupom


@router.delete("/{cupom_id}")
def excluir_cupom(cupom_id: int, db: Session = Depends(get_db)):
    db_cupom = db.query(CupomDesconto).filter(CupomDesconto.id == cupom_id).first()
    if not db_cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado.")

    db.delete(db_cupom)
    db.commit()
    return {"ok": True}


# ------------ Validação / simulação de aplicação de cupom -----------

class CupomAplicadoResponse(CupomSchema):
    valor_original: float
    valor_com_desconto: float
    desconto_aplicado: float


@router.get("/validar", response_model=CupomAplicadoResponse)
def validar_cupom(
    codigo: str = Query(..., description="Código do cupom"),
    valor: float = Query(..., description="Valor original"),
    tipo_aplicacao: str = Query("plano", description="plano/curso/aplicativo"),
    plano_nome: Optional[str] = Query(None),
    curso_id: Optional[int] = Query(None),
    aplicativo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    cupom = (
        db.query(CupomDesconto)
        .filter(CupomDesconto.codigo == codigo)
        .first()
    )

    if not cupom or not cupom.ativo:
        raise HTTPException(status_code=404, detail="Cupom inválido ou inativo.")

    # Verifica validade por data
    if cupom.valido_ate and cupom.valido_ate < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cupom vencido.")

    # Verifica limite de uso
    if cupom.limite_uso_total is not None and cupom.usos_realizados >= cupom.limite_uso_total:
        raise HTTPException(status_code=400, detail="Limite de uso do cupom atingido.")

    # Verifica se o tipo de aplicação bate
    if cupom.tipo_aplicacao != "todos" and cupom.tipo_aplicacao != tipo_aplicacao:
        raise HTTPException(status_code=400, detail="Cupom não se aplica a este tipo de compra.")

    # Se estiver amarrado a um plano específico
    if cupom.plano_nome and plano_nome and cupom.plano_nome != plano_nome:
        raise HTTPException(status_code=400, detail="Cupom não é válido para este plano.")

    # Se estiver amarrado a um curso específico
    if cupom.curso_id and curso_id and cupom.curso_id != curso_id:
        raise HTTPException(status_code=400, detail="Cupom não é válido para este curso.")

    # Se estiver amarrado a um aplicativo específico
    if cupom.aplicativo_id and aplicativo_id and cupom.aplicativo_id != aplicativo_id:
        raise HTTPException(status_code=400, detail="Cupom não é válido para este aplicativo.")

    # Cálculo do desconto
    if cupom.tipo_valor == "percentual":
        desconto = valor * (cupom.valor / 100.0)
    else:  # valor_fixo
        desconto = cupom.valor

    valor_com_desconto = max(0.0, valor - desconto)

    resposta = CupomAplicadoResponse(
        id=cupom.id,
        codigo=cupom.codigo,
        tipo_valor=cupom.tipo_valor,
        valor=cupom.valor,
        tipo_aplicacao=cupom.tipo_aplicacao,
        plano_nome=cupom.plano_nome,
        curso_id=cupom.curso_id,
        aplicativo_id=cupom.aplicativo_id,
        limite_uso_total=cupom.limite_uso_total,
        usos_realizados=cupom.usos_realizados,
        criado_em=cupom.criado_em,
        valido_ate=cupom.valido_ate,
        ativo=cupom.ativo,
        observacoes=cupom.observacoes,
        valor_original=valor,
        valor_com_desconto=valor_com_desconto,
        desconto_aplicado=desconto,
    )

    return resposta
