# backend/api/ideias.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import random
import re

from backend.database import get_db
from backend.api.auth import get_usuario_logado  # ajuste se seu projeto usa outro caminho
from backend.models import IdeiasMensais, Empresa  # Empresa precisa existir no seu models/__init__.py


router = APIRouter(prefix="/ideias", tags=["Central de Ideias"])


# =========================
# Helpers
# =========================

def _mes_ano_atual() -> str:
    # mantém simples; no frontend você já está em America/Sao_Paulo
    return datetime.now().strftime("%Y-%m")

def _slugify(texto: str) -> str:
    texto = (texto or "").strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_") or "card"

def _get_empresa_dados(empresa: Empresa) -> dict:
    # Tenta capturar o máximo possível sem quebrar se campos não existirem
    nome = getattr(empresa, "nome", None) or getattr(empresa, "nome_empresa", None) or "Sua Empresa"
    nicho = getattr(empresa, "nicho", None) or getattr(empresa, "segmento", None) or getattr(empresa, "ramo", None) or "Negócio"
    cidade = getattr(empresa, "cidade", None) or ""
    estado = getattr(empresa, "estado", None) or ""
    return {"nome": nome, "nicho": nicho, "cidade": cidade, "estado": estado}

def _categorias_base():
    # Categorias universais (serve para qualquer nicho)
    return [
        {"slug": "campanhas_datas_eventos", "titulo": "🎯 Campanhas, Datas e Eventos"},
        {"slug": "tendencias_novidades", "titulo": "🔥 Tendências e Novidades"},
        {"slug": "produtos_servicos_alta", "titulo": "🛍️ Produtos e Serviços em Alta"},
        {"slug": "conteudo_dados", "titulo": "📊 Dados e Estatísticas"},
        {"slug": "promocoes_ofertas", "titulo": "💰 Promoções e Ofertas"},
        {"slug": "branding_posicionamento", "titulo": "🧩 Branding e Posicionamento"},
        {"slug": "prova_social_autoridade", "titulo": "⭐ Prova Social e Autoridade"},
        {"slug": "relacionamento_comunidade", "titulo": "🤝 Relacionamento e Comunidade"},
    ]

def _ideias_conteudo_lote(empresa_nome: str, nicho: str, titulo_campanha: str, seed: int, lote: int):
    rnd = random.Random(seed + (lote * 1000))
    hashtags_base = [
        f"#{_slugify(nicho)}", "#marketingdigital", "#negocios", "#empreendedorismo",
        "#vendas", "#instagrambrasil", "#conteudodigital"
    ]

    temas = [
        "Dica prática", "Bastidores", "Antes e depois / prova", "Checklist rápido",
        "Mitos e verdades", "Erro comum + solução", "Passo a passo"
    ]

    itens = []
    for i in range(3):
        tema = rnd.choice(temas)
        cta = rnd.choice(["Chame no WhatsApp", "Peça um orçamento", "Agende agora", "Fale com a gente", "Clique no link da bio"])
        legenda = (
            f"{empresa_nome}: {tema} sobre {titulo_campanha}.\n\n"
            f"Se você trabalha com {nicho}, isso pode te ajudar hoje.\n\n"
            f"{cta}."
        )

        item = {
            "tema": f"{tema} — {titulo_campanha}",
            "criativo_estatico": f"Arte com título forte + 3 bullets sobre {titulo_campanha} (visual limpo e chamativo).",
            "criativo_video": f"Reels de 12–20s: abertura com dor do público, 2 dicas rápidas e CTA final.",
            "legenda": legenda,
            "hashtags": rnd.sample(list(set(hashtags_base + [f"#{_slugify(empresa_nome)}"])), k=min(8, len(set(hashtags_base + [f"#{_slugify(empresa_nome)}"]))))
        }
        itens.append(item)

    return {"lote": lote, "itens": itens}

def _dicas_branding_lote(nicho: str, titulo_campanha: str, seed: int, lote: int):
    rnd = random.Random(seed + (lote * 2000))
    dicas_pool = [
        "Padronize a identidade visual: tipografia, cores e espaçamentos consistentes em todos os posts.",
        "Defina um tom de voz fixo (prático, acolhedor, técnico, premium) e use sempre o mesmo padrão.",
        "Crie uma promessa clara: ‘o que o cliente ganha’ em uma frase curta e repetível.",
        "Use prova social com contexto (o que mudou + em quanto tempo + resultado).",
        "Mantenha CTA e oferta simples: 1 ação por post (não misturar 3 objetivos).",
        "Crie 2–3 modelos de posts (templates) para reconhecimento visual instantâneo.",
        "Tenha um ‘diferencial principal’ e repita semanalmente em formatos diferentes.",
        "Evite promoções genéricas: nomeie a campanha e crie uma narrativa (começo/meio/fim).",
    ]
    rnd.shuffle(dicas_pool)
    itens = [f"[{nicho}] {dicas_pool[i]} (tema: {titulo_campanha})" for i in range(3)]
    return {"lote": lote, "itens": itens}

def _montar_card(cat_slug: str, idx: int, empresa_nome: str, nicho: str, mes_ano: str, seed_base: int):
    import random

    # Datas sugeridas: espalha ao longo do mês para dar “agenda”
    dia = min(28, 3 + (idx * 4))
    data_sugerida = f"{mes_ano}-{dia:02d}"

    campanhas_por_categoria = {
        "campanhas_datas_eventos": ["Campanha do Mês", "Oportunidade da Semana", "Ação Relâmpago"],
        "tendencias_novidades": ["Tendência em Alta", "Novo Hábito do Cliente", "Formato que performa"],
        "produtos_servicos_alta": ["Top 3 do Mês", "Serviço Destaque", "Combo Inteligente"],
        "conteudo_dados": ["Mitos e Verdades", "Dados Surpreendentes", "Erros Comuns"],
        "promocoes_ofertas": ["Oferta Limitada", "Pacote Especial", "Condição Exclusiva"],
        "branding_posicionamento": ["Diferencial Claro", "Tom de Voz", "Consistência Visual"],
        "prova_social_autoridade": ["Depoimento + Caso", "Resultado Real", "Bastidores Profissionais"],
        "relacionamento_comunidade": ["Bastidores", "História/Propósito", "Perguntas & Respostas"],
    }

    descricoes_por_categoria = {
        "campanhas_datas_eventos": (
            f"📅 Ideia baseada em **datas, eventos e oportunidades do mês** para o nicho de **{nicho}**. "
            f"Use para criar ações com prazo e motivo claro para o cliente agir."
        ),
        "tendencias_novidades": (
            f"🔥 Ideia baseada em **tendências e novidades** que estão funcionando no nicho de **{nicho}**. "
            f"Use para se manter atual e ganhar alcance com formatos do momento."
        ),
        "produtos_servicos_alta": (
            f"⭐ Ideia focada em **produtos/serviços em alta** no nicho de **{nicho}**. "
            f"Use para destacar o que mais vende e criar ofertas inteligentes."
        ),
        "conteudo_dados": (
            f"📊 Ideia com **dados, curiosidades e informações** relevantes do nicho de **{nicho}**. "
            f"Use para educar, gerar autoridade e aumentar confiança."
        ),
        "promocoes_ofertas": (
            f"🏷️ Ideia de **promoção/oferta** pensada para conversão no nicho de **{nicho}**. "
            f"Use com CTA direto e condição clara."
        ),
        "branding_posicionamento": (
            f"🎨 Ideia focada em **branding e posicionamento**, para fortalecer a percepção da marca no nicho de **{nicho}**. "
            f"Use para padronizar e comunicar valor."
        ),
        "prova_social_autoridade": (
            f"🏆 Ideia de **prova social e autoridade** no nicho de **{nicho}**. "
            f"Use para mostrar resultados, casos reais e credibilidade."
        ),
        "relacionamento_comunidade": (
            f"🤝 Ideia para **relacionamento e comunidade** no nicho de **{nicho}**. "
            f"Use para gerar interação, proximidade e recorrência."
        ),
    }

    # Define o título base conforme a categoria
    rng = random.Random(seed_base + idx)
    titulo_base = rng.choice(campanhas_por_categoria.get(cat_slug, ["Campanha"]))

    # Título final (mais natural)
    titulo = f"{titulo_base} — {nicho}"

    # ID mais estável/curto (evita ficar gigante e reduz chance de conflito)
    # Mantém categoria + idx + slug parcial
    card_id = f"{cat_slug[:3]}_{idx:03d}_{_slugify(titulo)[:24]}"

    # Descrição conforme a categoria (fallback seguro)
    descricao = descricoes_por_categoria.get(
        cat_slug,
        f"💡 Ideia sugerida para **{empresa_nome}** no nicho de **{nicho}**."
    )

    # Lotes iniciais
    conteudos = [_ideias_conteudo_lote(empresa_nome, nicho, titulo, seed_base + idx, lote=1)]
    branding = [_dicas_branding_lote(nicho, titulo, seed_base + idx, lote=1)]

    return {
        "id": card_id,
        "titulo": titulo,
        "data_sugerida": data_sugerida,
        "descricao": descricao,
        "favorito": False,
        "conteudos": conteudos,
        "branding": branding,
        "limites": {"max_lotes_conteudo": 5, "max_lotes_branding": 5}
    }


def _gerar_pacote_mes(empresa: Empresa, mes_ano: str, setor: str | None):
    dados = _get_empresa_dados(empresa)
    empresa_nome = dados["nome"]
    nicho = dados["nicho"]

    # Seed estável por empresa+mes para evitar “mudar tudo” do nada
    seed_base = abs(hash(f"{empresa.id}-{mes_ano}-{empresa_nome}-{nicho}")) % (10**9)

    categorias = []
    for cat in _categorias_base():
        # 2 cards por categoria = 16 cards. Se quiser mais, é só subir para 3.
        cards = []
        for i in range(1, 3):
            cards.append(_montar_card(cat["slug"], idx=(len(categorias) * 10 + i), empresa_nome=empresa_nome, nicho=nicho, mes_ano=mes_ano, seed_base=seed_base))
        categorias.append({"slug": cat["slug"], "titulo": cat["titulo"], "cards": cards})

    return {
        "empresa_id": empresa.id,
        "mes_ano": mes_ano,
        "setor": setor,
        "empresa_nome": empresa_nome,
        "nicho": nicho,
        "categorias": categorias,
        "criado_em": datetime.utcnow().isoformat()
    }

def _achar_card(conteudo: dict, card_id: str):
    for cat in conteudo.get("categorias", []):
        for card in cat.get("cards", []):
            if card.get("id") == card_id:
                return card
    return None


# =========================
# Schemas
# =========================

class GerarIdeiasBody(BaseModel):
    empresa_id: int
    mes_ano: str | None = None  # se None, usa mês atual
    setor: str | None = None

class GerarMaisBody(BaseModel):
    empresa_id: int
    mes_ano: str
    card_id: str
    tipo: str  # "conteudo" ou "branding"

class FavoritarBody(BaseModel):
    empresa_id: int
    mes_ano: str
    card_id: str
    favorito: bool


# =========================
# Endpoints
# =========================

@router.get("/{empresa_id}/{mes_ano}")
def obter_ideias_mes(
    empresa_id: int,
    mes_ano: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    reg = db.query(IdeiasMensais).filter(
        IdeiasMensais.empresa_id == empresa_id,
        IdeiasMensais.mes_ano == mes_ano
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Nenhuma ideia encontrada para este mês.")

    return {"empresa_id": empresa_id, "mes_ano": mes_ano, "setor": reg.setor, "conteudo": reg.conteudo}


@router.post("/gerar")
def gerar_ideias_mes(
    body: GerarIdeiasBody,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    mes_ano = body.mes_ano or _mes_ano_atual()

    empresa = db.query(Empresa).filter(Empresa.id == body.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # Se já existe, devolve o existente
    existente = db.query(IdeiasMensais).filter(
        IdeiasMensais.empresa_id == body.empresa_id,
        IdeiasMensais.mes_ano == mes_ano
    ).first()
    if existente:
        return {"status": "ja_existia", "empresa_id": body.empresa_id, "mes_ano": mes_ano, "conteudo": existente.conteudo}

    conteudo = _gerar_pacote_mes(empresa, mes_ano, body.setor)

    novo = IdeiasMensais(
        empresa_id=body.empresa_id,
        mes_ano=mes_ano,
        setor=body.setor,
        conteudo=conteudo
    )

    db.add(novo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Se deu corrida (dois cliques), retorna o existente
        reg = db.query(IdeiasMensais).filter(
            IdeiasMensais.empresa_id == body.empresa_id,
            IdeiasMensais.mes_ano == mes_ano
        ).first()
        if reg:
            return {"status": "ja_existia", "empresa_id": body.empresa_id, "mes_ano": mes_ano, "conteudo": reg.conteudo}
        raise

    db.refresh(novo)
    return {"status": "criado", "empresa_id": body.empresa_id, "mes_ano": mes_ano, "conteudo": novo.conteudo}


@router.post("/gerar-mais")
def gerar_mais_por_card(
    body: GerarMaisBody,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    reg = db.query(IdeiasMensais).filter(
        IdeiasMensais.empresa_id == body.empresa_id,
        IdeiasMensais.mes_ano == body.mes_ano
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Pacote do mês não encontrado. Gere primeiro.")

    conteudo = reg.conteudo
    card = _achar_card(conteudo, body.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card não encontrado.")

    empresa_nome = conteudo.get("empresa_nome", "Sua Empresa")
    nicho = conteudo.get("nicho", "Negócio")
    titulo = card.get("titulo", "Campanha")
    seed_base = abs(hash(f"{body.empresa_id}-{body.mes_ano}-{body.card_id}-{empresa_nome}-{nicho}")) % (10**9)

    tipo = (body.tipo or "").strip().lower()
    if tipo not in ("conteudo", "branding"):
        raise HTTPException(status_code=400, detail="Tipo inválido. Use 'conteudo' ou 'branding'.")

    if tipo == "conteudo":
        lotes = card.get("conteudos", [])
        max_lotes = (card.get("limites") or {}).get("max_lotes_conteudo", 5)
        prox_lote = len(lotes) + 1
        if prox_lote > max_lotes:
            raise HTTPException(status_code=400, detail="Limite mensal de lotes de conteúdo atingido para este card.")
        lotes.append(_ideias_conteudo_lote(empresa_nome, nicho, titulo, seed_base, lote=prox_lote))
        card["conteudos"] = lotes

    if tipo == "branding":
        lotes = card.get("branding", [])
        max_lotes = (card.get("limites") or {}).get("max_lotes_branding", 5)
        prox_lote = len(lotes) + 1
        if prox_lote > max_lotes:
            raise HTTPException(status_code=400, detail="Limite mensal de lotes de branding atingido para este card.")
        lotes.append(_dicas_branding_lote(nicho, titulo, seed_base, lote=prox_lote))
        card["branding"] = lotes

    reg.conteudo = conteudo
    db.add(reg)
    db.commit()
    db.refresh(reg)

    return {"status": "ok", "empresa_id": body.empresa_id, "mes_ano": body.mes_ano, "conteudo": reg.conteudo}


@router.post("/favoritar")
def favoritar_card(
    body: FavoritarBody,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    reg = db.query(IdeiasMensais).filter(
        IdeiasMensais.empresa_id == body.empresa_id,
        IdeiasMensais.mes_ano == body.mes_ano
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Pacote do mês não encontrado. Gere primeiro.")

    conteudo = reg.conteudo
    card = _achar_card(conteudo, body.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card não encontrado.")

    card["favorito"] = bool(body.favorito)

    reg.conteudo = conteudo
    db.add(reg)
    db.commit()
    db.refresh(reg)

    return {"status": "ok", "favorito": card["favorito"], "empresa_id": body.empresa_id, "mes_ano": body.mes_ano}
