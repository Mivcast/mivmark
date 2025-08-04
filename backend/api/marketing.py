from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, sessionmaker
from backend.database import engine, get_db
from backend.models import CardMarketing, Usuario
from datetime import datetime
from typing import List
from pydantic import BaseModel
from backend.api.auth import get_current_user

router = APIRouter()
SessionLocal = sessionmaker(bind=engine)

class CardSchema(BaseModel):
    id: int
    titulo: str
    descricao: str
    fonte: str
    ideias_conteudo: str
    tipo: str
    mes_referencia: str
    favorito: bool
    eh_atualizacao: bool
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True

class GerarCardsInput(BaseModel):
    nicho: str
    mes: str

# 🚀 Gerador mock se não houver cards
def gerar_mock_cards(usuario_id: int, mes: str):
    tipos = {
        "Campanha": "Campanha: sites - Dica #",
        "Tendência": "Tendência: Atendimento com IA #",
        "Produto": "Produto popular #",
        "Dado": "Estatística relevante #",
        "Conteúdo": "Conteúdo estratégico #",
        "Promoção": "Desconto imperdível #",
        "Conscientização": "Campanha do Bem #"
    }

    cards = []
    for tipo, base_titulo in tipos.items():
        for i in range(10):
            cards.append(CardMarketing(
                usuario_id=usuario_id,
                titulo=f"{base_titulo}{i+1}",
                descricao=f"Atualização sobre {tipo.lower()} para o mês {mes}.",
                fonte="https://exemplo.com",
                ideias_conteudo="1. Exemplo 1\n2. Exemplo 2\n3. Exemplo 3",
                tipo=tipo,
                mes_referencia=mes,
                favorito=False,
                eh_atualizacao=True,
                criado_em=datetime.utcnow(),
                atualizado_em=datetime.utcnow()
            ))
    return cards

@router.get("/marketing/cards/{mes}", response_model=List[CardSchema])
def listar_cards_mes(mes: str, usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()
    cards = db.query(CardMarketing).filter_by(usuario_id=usuario.id, mes_referencia=mes).all()

    if not cards:
        cards_mock = gerar_mock_cards(usuario.id, mes)
        db.add_all(cards_mock)
        db.commit()
        cards = db.query(CardMarketing).filter_by(usuario_id=usuario.id, mes_referencia=mes).all()

    return cards

@router.post("/marketing/favoritar/{card_id}")
def favoritar_card(card_id: int, usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()
    card = db.get(CardMarketing, card_id)
    if not card or card.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Card não encontrado.")
    card.favorito = not card.favorito
    db.commit()
    return {"mensagem": "Card atualizado com sucesso", "favorito": card.favorito}

@router.get("/marketing/favoritos", response_model=List[CardSchema])
def listar_favoritos(usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()
    cards = db.query(CardMarketing).filter_by(usuario_id=usuario.id, favorito=True).order_by(CardMarketing.atualizado_em.desc()).all()
    return cards

@router.post("/marketing/gerar_cards")
def gerar_cards(input: GerarCardsInput, usuario: Usuario = Depends(get_current_user)):
    db = SessionLocal()

    exemplo = [
        {
            "titulo": "Tendência: Produtos Sustentáveis em Alta",
            "descricao": "Consumidores buscam mais produtos ecológicos e biodegradáveis.",
            "fonte": "https://noticia.com/sustentaveis",
            "ideias_conteudo": "1. Post sobre embalagens ecológicas\n2. Story com bastidores de produção sustentável\n3. Campanha de conscientização no feed",
            "tipo": "Tendência"
        },
        {
            "titulo": "Campanha: Dia do Cliente em Setembro",
            "descricao": "Prepare ações especiais para 15/09, data oficial do Dia do Cliente.",
            "fonte": "https://marketing.com/dia-cliente",
            "ideias_conteudo": "1. Cupom de desconto exclusivo\n2. Post com depoimentos de clientes\n3. Série de stories agradecendo clientes fiéis",
            "tipo": "Campanha"
        }
    ]

    for e in exemplo:
        novo_card = CardMarketing(
            usuario_id=usuario.id,
            titulo=e["titulo"],
            descricao=e["descricao"],
            fonte=e["fonte"],
            ideias_conteudo=e["ideias_conteudo"],
            tipo=e["tipo"],
            mes_referencia=input.mes,
            favorito=False,
            eh_atualizacao=False,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow()
        )
        db.add(novo_card)

    db.commit()
    return {"mensagem": f"{len(exemplo)} cards gerados com sucesso."}

@router.get("/marketing/populares")
def listar_cards_populares(limit: int = Query(10), db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    cards = (
        db.query(CardMarketing)
        .filter(CardMarketing.favorito == True)
        .order_by(CardMarketing.atualizado_em.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": c.id,
            "titulo": c.titulo,
            "descricao": c.descricao,
            "fonte": c.fonte,
            "ideias_conteudo": c.ideias_conteudo,
            "tipo": c.tipo,
            "mes_referencia": c.mes_referencia,
            "criado_em": c.criado_em,
            "atualizado_em": c.atualizado_em
        }
        for c in cards
    ]
