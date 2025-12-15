# backend/api/consultor_mensal.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import random

from backend.database import get_db
from backend.api.auth import get_usuario_logado
from backend.models import Empresa
from backend.models.consultor_mensal import ConsultorMensal

router = APIRouter(prefix="/consultor-mensal", tags=["Consultor Mensal"])


# =========================
# Schemas
# =========================
class GerarBody(BaseModel):
    versao: int | None = None


# =========================
# Compat: usuario dict OU objeto
# =========================
def _get_usuario_id(usuario) -> int:
    """
    Seu get_usuario_logado pode retornar:
    - dict {"id": ...}
    - objeto SQLAlchemy Usuario com atributo .id
    """
    if isinstance(usuario, dict):
        return int(usuario.get("id"))
    return int(getattr(usuario, "id"))


# =========================
# Helpers de geração
# =========================
def _seed(empresa_id: int, mes_ano: str, empresa_nome: str, nicho: str, extra: str = "") -> int:
    base = f"{empresa_id}|{mes_ano}|{empresa_nome}|{nicho}|{extra}"
    return abs(hash(base)) % (10**9)


def _mes_nome_pt(mes_ano: str) -> str:
    try:
        ano = int(mes_ano.split("-")[0])
        mes = int(mes_ano.split("-")[1])
    except Exception:
        return mes_ano
    nomes = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
    return f"{nomes[mes-1]} de {ano}"


def _datas_relevantes_por_mes(mes_ano: str):
    mes = mes_ano.split("-")[1] if "-" in mes_ano else ""
    if mes == "12":
        return [
            ("Natal", "12-25"),
            ("Réveillon", "12-31"),
            ("Compras de fim de ano", None),
        ]
    if mes == "11":
        return [
            ("Black Friday", None),
            ("Aquecimento de fim de ano", None),
        ]
    return [
        ("Oportunidade do mês", None),
        ("Tema sazonal do período", None),
    ]


def _blocos_padrao():
    return [
        ("campanhas_datas_eventos", "🎯 Campanhas, Datas e Eventos"),
        ("tendencias_novidades", "🚀 Tendências e Novidades"),
        ("dados_estatisticas", "📊 Dados e Estatísticas"),
        ("produtos_servicos_alta", "🔥 Produtos/Serviços em alta"),
        ("promocoes_ofertas", "🏷️ Promoções e Ofertas"),
        ("branding_posicionamento", "🧠 Branding e Posicionamento"),
        ("prova_social_autoridade", "🏆 Prova Social e Autoridade"),
        ("relacionamento_comunidade", "🤝 Relacionamento e Comunidade"),
    ]


def _gerar_item_conteudo(rng: random.Random, empresa_nome: str, nicho: str, tema_base: str, numero: int):
    assunto = rng.choice([
        f"Mitos e verdades sobre {tema_base}",
        f"Passo a passo para aplicar {tema_base}",
        f"Erro comum + solução em {tema_base}",
        f"Checklist rápido de {tema_base}",
        f"Antes e depois / prova real de {tema_base}",
        f"Dica prática para {tema_base}",
    ])

    cta = rng.choice(["Chame no WhatsApp.", "Peça um orçamento.", "Clique no link da bio.", "Agende agora.", "Salve este post."])
    hashtags = rng.sample([
        "#marketingdigital", "#negocios", "#empreendedorismo", "#instagrambrasil", "#conteudodigital",
        f"#{nicho.replace(' ', '_')}".lower(), f"#{empresa_nome.replace(' ', '').lower()}",
        "#vendas", "#branding"
    ], k=6)

    legenda = (
        f"✨ {empresa_nome}: {assunto}\n\n"
        f"Se você trabalha com {nicho}, isso pode te ajudar hoje.\n\n"
        f"✅ Quer que eu adapte isso para o seu serviço/produto? {cta}\n\n"
        + " ".join(hashtags)
    )

    return {
        "numero": numero,
        "assunto": assunto,
        "criativo_imagem": f"Arte com título forte + 3 bullets sobre: {assunto} (visual limpo e chamativo).",
        "criativo_video": "Reels 12–20s: abertura com dor do público, 2 dicas rápidas e CTA final.",
        "legenda": legenda
    }


def _gerar_dica_branding(rng: random.Random, tema_base: str, numero: int):
    dicas = [
        "Padronize identidade visual: tipografia, cores e espaçamentos consistentes em todos os posts.",
        "Crie uma promessa clara em 1 frase: o que o cliente ganha (curta e repetível).",
        "Use prova social com contexto (o que mudou + em quanto tempo + resultado).",
        "Reforce o diferencial em todo post: 1 frase fixa no final (assinatura da marca).",
        "Diminua esforço do cliente: CTA simples e único (não dê 3 caminhos ao mesmo tempo).",
        "Defina 3 pilares de conteúdo e repita com variações (consistência vence criatividade solta).",
    ]
    return {
        "numero": numero,
        "texto": f"{rng.choice(dicas)} (tema: {tema_base})"
    }


def _gerar_pacote(empresa_id: int, mes_ano: str, empresa_nome: str, nicho: str, versao: int = 1):
    seed = _seed(empresa_id, mes_ano, empresa_nome, nicho, extra=str(versao))
    rng = random.Random(seed)

    mes_pt = _mes_nome_pt(mes_ano)
    datas = _datas_relevantes_por_mes(mes_ano)

    resumo_executivo = (
        f"Neste mês ({mes_pt}), você tem oportunidades claras para fortalecer a marca e gerar demanda no nicho de {nicho}.\n"
        f"Abaixo, eu organizei campanhas, tendências e ações práticas para {empresa_nome}, com ideias prontas (imagem/vídeo) e legendas copiáveis."
    )

    blocos = []
    for slug, titulo in _blocos_padrao():
        if slug == "campanhas_datas_eventos":
            foco = rng.choice(datas)
            foco_nome = foco[0]
            intro = (
                f"📌 Contexto do mês: {foco_nome} costuma puxar atenção e intenção de compra.\n"
                f"{empresa_nome} pode aproveitar isso com conteúdo educativo + oferta clara + prova social."
            )
        elif slug == "tendencias_novidades":
            intro = (
                f"🚀 Aqui vão tendências que estão performando bem em negócios de {nicho}.\n"
                f"A ideia é você postar com consistência e linguagem simples, sem complicar."
            )
        elif slug == "dados_estatisticas":
            intro = (
                f"📊 Pessoas confiam em dados. Use números e comparações simples para aumentar autoridade.\n"
                f"Mesmo sem pesquisas complexas, dá para transformar fatos do dia a dia em ‘estatísticas úteis’."
            )
        else:
            intro = (
                f"✅ Sugestões práticas e fáceis de aplicar para {empresa_nome} no nicho de {nicho}.\n"
                f"Use como roteiro de posts, stories e ofertas."
            )

        tema_base = titulo.replace("🎯", "").replace("🚀", "").replace("📊", "").replace("🔥", "").replace("🏷️", "").replace("🧠", "").replace("🏆", "").replace("🤝", "").strip()

        conteudos = [_gerar_item_conteudo(rng, empresa_nome, nicho, tema_base, i) for i in range(1, 4)]
        branding = [_gerar_dica_branding(rng, tema_base, i) for i in range(1, 4)]

        blocos.append({
            "slug": slug,
            "titulo": titulo,
            "intro": intro,
            "favorito": False,
            "conteudos": conteudos,
            "branding": branding,
        })

    return {
        "empresa_id": empresa_id,
        "empresa_nome": empresa_nome,
        "nicho": nicho,
        "mes_ano": mes_ano,
        "versao": versao,
        "resumo_executivo": resumo_executivo,
        "blocos": blocos,
        "atualizado_em": datetime.utcnow().isoformat(),
    }


# =========================
# Rotas
# =========================
@router.get("/{empresa_id}/{mes_ano}")
def obter_consultoria_mes(
    empresa_id: int,
    mes_ano: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    usuario_id = _get_usuario_id(usuario)

    reg = db.query(ConsultorMensal).filter(
        ConsultorMensal.usuario_id == usuario_id,
        ConsultorMensal.empresa_id == empresa_id,
        ConsultorMensal.mes_ano == mes_ano
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Nenhuma consultoria gerada para este mês.")

    return {"status": "ok", "conteudo": reg.conteudo}


@router.post("/gerar/{empresa_id}/{mes_ano}")
def gerar_consultoria_mes(
    empresa_id: int,
    mes_ano: str,
    body: GerarBody | None = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    usuario_id = _get_usuario_id(usuario)

    empresa = db.query(Empresa).filter(
        Empresa.id == empresa_id,
        Empresa.usuario_id == usuario_id
    ).first()

    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada para este usuário.")

    reg = db.query(ConsultorMensal).filter(
        ConsultorMensal.usuario_id == usuario_id,
        ConsultorMensal.empresa_id == empresa_id,
        ConsultorMensal.mes_ano == mes_ano
    ).first()

    if reg:
        return {"status": "ok", "conteudo": reg.conteudo, "mensagem": "Já existe consultoria para este mês."}

    conteudo = _gerar_pacote(
        empresa_id=empresa_id,
        mes_ano=mes_ano,
        empresa_nome=getattr(empresa, "nome_empresa", None) or getattr(empresa, "nome", None) or "Sua Empresa",
        nicho=getattr(empresa, "nicho", None) or "Negócio",
        versao=1
    )

    reg = ConsultorMensal(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        mes_ano=mes_ano,
        conteudo=conteudo,
        criado_em=datetime.utcnow(),
        atualizado_em=datetime.utcnow(),
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    return {"status": "ok", "conteudo": reg.conteudo}


@router.post("/regerar/{empresa_id}/{mes_ano}")
def regerar_consultoria_mes(
    empresa_id: int,
    mes_ano: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_logado),
):
    usuario_id = _get_usuario_id(usuario)

    empresa = db.query(Empresa).filter(
        Empresa.id == empresa_id,
        Empresa.usuario_id == usuario_id
    ).first()

    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada para este usuário.")

    reg = db.query(ConsultorMensal).filter(
        ConsultorMensal.usuario_id == usuario_id,
        ConsultorMensal.empresa_id == empresa_id,
        ConsultorMensal.mes_ano == mes_ano
    ).first()

    versao_atual = 1
    if reg and isinstance(reg.conteudo, dict):
        try:
            versao_atual = int(reg.conteudo.get("versao", 1))
        except Exception:
            versao_atual = 1

    nova_versao = versao_atual + 1
    conteudo = _gerar_pacote(
        empresa_id=empresa_id,
        mes_ano=mes_ano,
        empresa_nome=getattr(empresa, "nome_empresa", None) or getattr(empresa, "nome", None) or "Sua Empresa",
        nicho=getattr(empresa, "nicho", None) or "Negócio",
        versao=nova_versao
    )

    if not reg:
        reg = ConsultorMensal(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            mes_ano=mes_ano,
            conteudo=conteudo,
            criado_em=datetime.utcnow(),
            atualizado_em=datetime.utcnow(),
        )
        db.add(reg)
    else:
        reg.conteudo = conteudo
        reg.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(reg)

    return {"status": "ok", "conteudo": reg.conteudo}
