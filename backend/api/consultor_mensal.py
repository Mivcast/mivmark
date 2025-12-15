# backend/api/consultor_mensal.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime
import random

from backend.database import get_db
from backend.api.auth import get_usuario_logado
from backend.models import Empresa
from backend.models.consultor_mensal import ConsultorMensal
from backend.services.inteligencia_mercado import obter_insumos

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


def _qtd_cards_por_bloco(rng: random.Random, slug: str) -> int:
    # Aqui fica do jeito que você pediu: pode passar de 3, e cada bloco pode ter volumes diferentes.
    if slug == "campanhas_datas_eventos":
        return rng.randint(6, 12)
    if slug == "tendencias_novidades":
        return rng.randint(4, 8)
    if slug == "dados_estatisticas":
        return rng.randint(3, 6)
    if slug == "produtos_servicos_alta":
        return rng.randint(4, 8)
    if slug == "promocoes_ofertas":
        return rng.randint(4, 10)
    if slug == "branding_posicionamento":
        return rng.randint(3, 5)
    if slug == "prova_social_autoridade":
        return rng.randint(3, 6)
    if slug == "relacionamento_comunidade":
        return rng.randint(3, 6)
    return 4


def _limpar_emoji(titulo: str) -> str:
    return (
        titulo.replace("🎯", "")
              .replace("🚀", "")
              .replace("📊", "")
              .replace("🔥", "")
              .replace("🏷️", "")
              .replace("🧠", "")
              .replace("🏆", "")
              .replace("🤝", "")
              .strip()
    )


def _bullets_praticos(rng: random.Random, nicho: str, foco_nome: str | None) -> list[str]:
    # Bullets sempre práticos e adaptáveis a qualquer nicho.
    # (Exemplo: vegano no Réveillon fica natural, mas serve pra qualquer área)
    foco_txt = f"no {foco_nome}" if foco_nome else "neste mês"
    opcoes = [
        f"Entrada (rápida): indique uma opção simples e útil para o público {foco_txt}.",
        "Prato principal (conteúdo): mostre 1 solução completa (passo a passo curto).",
        "Sobremesa (CTA): finalize com uma chamada simples (orçamento / WhatsApp / link da bio).",
        "Checklist do cliente: 3 itens para ele não errar (bem objetivo).",
        "Erro comum + correção: mostre o antes/depois de forma clara.",
        "Oferta inteligente: sugestão de combo/pacote e prazo (sem complicar).",
        "Prova social: 1 mini depoimento + contexto (o que mudou + resultado).",
        "Bastidores: mostre o processo real em 10–15s (aumenta confiança).",
    ]
    rng.shuffle(opcoes)
    return opcoes[:3]


def _gerar_item_conteudo(
    rng: random.Random,
    empresa_nome: str,
    nicho: str,
    tema_base: str,
    numero: int,
    foco_nome: str | None = None,
    mes_pt: str | None = None
):
    # =========================
    # Títulos mais “humanos” e específicos
    # =========================
    if foco_nome:
        assunto = rng.choice([
            f"Dica prática para {nicho} na época do {foco_nome}",
            f"O que vender/mostrar no {foco_nome} (ideias para {nicho})",
            f"Checklist do {foco_nome}: como sua empresa pode aproveitar",
            f"Erros comuns no {foco_nome} e como evitar",
        ])
    else:
        assunto = rng.choice([
            f"Dica prática para {tema_base} no nicho de {nicho}",
            f"Passo a passo simples de {tema_base} para {nicho}",
            f"Erro comum + solução em {tema_base} (para {nicho})",
            f"Checklist rápido de {tema_base} para sua empresa",
        ])

    # =========================
    # Texto no estilo que você pediu
    # =========================
    foco_txt = f"neste mês ({mes_pt})" if mes_pt else "neste mês"
    contexto = ""
    if foco_nome:
        contexto = f"📌 {foco_txt}, o {foco_nome} costuma puxar atenção e intenção de compra. Sua empresa pode aproveitar isso com conteúdo educativo + oferta clara + prova social."
    else:
        contexto = f"📌 {foco_txt}, sua empresa pode fortalecer presença e gerar demanda com conteúdo simples e consistente."

    bullets = _bullets_praticos(rng, nicho, foco_nome)
    bullets_txt = "\n".join([f"▪️ {b}" for b in bullets])

    cta = rng.choice([
        "Peça um orçamento no WhatsApp.",
        "Chame no WhatsApp e eu adapto pro seu caso.",
        "Clique no link da bio e fale com a gente.",
        "Salve este post e me chama para adaptar para sua empresa.",
    ])

    hashtags = rng.sample([
        "#marketingdigital", "#negocios", "#empreendedorismo", "#instagrambrasil", "#conteudodigital",
        f"#{nicho.replace(' ', '_')}".lower(),
        f"#{empresa_nome.replace(' ', '').lower()}",
        "#vendas", "#branding"
    ], k=6)

    legenda = (
        f"🎯 {tema_base}\n\n"
        f"{contexto}\n\n"
        f"💡 Ideias de Conteúdo sobre {foco_nome} para sua empresa\n" if foco_nome else
        f"💡 Ideias de Conteúdo para sua empresa\n"
    )
    legenda += (
        f"{numero}º Ideia: {assunto}\n\n"
        f"✍️ Legenda pronta para copiar:\n\n"
        f"✨ Dicas da {empresa_nome}:\n"
        f"{bullets_txt}\n\n"
        f"✅ Use essas dicas e tenha resultados de forma simples.\n"
        f"✅ {cta}\n\n"
        + " ".join(hashtags)
    )

    # Criativos mais “mandando fazer”, do jeito direto
    criativo_imagem = (
        "Use uma arte com título forte + 3 pontos práticos.\n"
        "Visual limpo, texto grande, contraste bom e 1 CTA discreto."
    )

    criativo_video = (
        "Crie um Reel 12–20s:\n"
        "1) Gancho (dor do cliente)\n"
        "2) 2 dicas rápidas\n"
        "3) CTA final (WhatsApp / orçamento / link da bio)"
    )

    return {
        "numero": numero,
        "assunto": assunto,
        "criativo_imagem": criativo_imagem,
        "criativo_video": criativo_video,
        "legenda": legenda
    }


def _gerar_item_conteudo_real(
    rng: random.Random,
    empresa_nome: str,
    nicho: str,
    tema_real: str,
    numero: int,
    mes_ano: str,
    dado_texto: str = "",
    dado_fonte: str = ""
):
    cta = rng.choice(["Peça um orçamento.", "Chame no WhatsApp.", "Clique no link da bio.", "Agende agora.", "Salve este post."])

    # legenda pronta (com 3 bullets de ação)
    bullets = []

    # Se for um “Dado”, usa o texto real
    if dado_texto:
        bullets = [
            f"Dado do mês: {dado_texto}",
            "Como usar: coloque esse dado no 1º slide/reels e explique em 10s o que ele significa.",
            "CTA: finalize com uma oferta simples (ex.: orçamento / reserva / combo)."
        ]
        if dado_fonte:
            bullets.append(f"Fonte: {dado_fonte}")
    else:
        bullets = [
            f"O que fazer: use o tema “{tema_real}” como assunto central do post.",
            "Como fazer: explique em 3 pontos (problema → dica → resultado).",
            f"CTA: {cta}"
        ]

    hashtags = rng.sample([
        "#marketingdigital", "#instagrambrasil", "#vendas", "#branding",
        f"#{nicho.replace(' ', '_')}".lower(),
        f"#{empresa_nome.replace(' ', '').lower()}",
        "#negocios", "#conteudo"
    ], k=6)

    legenda = (
        f"✨ {empresa_nome} — Ideia #{numero} para {mes_ano}\n"
        f"Tema: {tema_real}\n\n"
        + "\n".join([f"▪️ {b}" for b in bullets])
        + "\n\n"
        + " ".join(hashtags)
    )

    return {
        "numero": numero,
        "assunto": tema_real,
        "criativo_imagem": f"Use uma arte com título forte + 3 pontos práticos sobre: {tema_real}.",
        "criativo_video": "Crie um Reel 12–20s: dor do público → 2 dicas rápidas → CTA final.",
        "legenda": legenda
    }





def _gerar_dica_branding(rng: random.Random, tema_base: str, numero: int):
    # Você disse que branding está perfeito -> mantive como está.
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


def _gerar_pacote(
    empresa_id: int,
    mes_ano: str,
    empresa_nome: str,
    nicho: str,
    versao: int = 1
):
    seed = _seed(empresa_id, mes_ano, empresa_nome, nicho, extra=str(versao))
    rng = random.Random(seed)

    mes_pt = _mes_nome_pt(mes_ano)
    datas = _datas_relevantes_por_mes(mes_ano)
    insumos = obter_insumos(mes_ano=mes_ano, nicho=nicho)

    resumo_executivo = (
        f"📌 Planejamento do mês: {mes_pt}\n\n"
        f"Este material foi montado para você bater o olho e pensar:\n"
        f"“Nossa, quanta ideia boa para usar ao longo do mês”.\n\n"
        f"As sugestões abaixo são práticas, organizadas por tema e "
        f"pensadas para o nicho de {nicho}."
    )

    blocos = []

    for slug, titulo in _blocos_padrao():
        tema_base = _limpar_emoji(titulo)
        foco_nome = None
        temas_reais: list[str] = []
        intro = ""

        # 🎯 CAMPANHAS, DATAS E EVENTOS
        if slug == "campanhas_datas_eventos":
            foco = rng.choice(datas)
            foco_nome = foco[0]

            intro = (
                f"📌 Neste mês ({mes_pt}), o {foco_nome} costuma puxar atenção "
                f"e intenção de compra. Sua empresa pode aproveitar isso com "
                f"conteúdo educativo + oferta clara + prova social."
            )

            temas_reais = [foco_nome]

        # 🚀 TENDÊNCIAS E NOVIDADES
        elif slug == "tendencias_novidades":
            intro = (
                f"🚀 Tendências reais do mês no nicho de {nicho}. "
                f"Esses assuntos estão chamando atenção e podem virar "
                f"posts, Reels e Stories facilmente."
            )

            temas_reais = insumos.tendencias

        # 📊 DADOS E ESTATÍSTICAS
        elif slug == "dados_estatisticas":
            intro = (
                f"📊 Dados e estatísticas ajudam o cliente a confiar mais. "
                f"Use esses números como gancho de autoridade nos seus conteúdos."
            )

            temas_reais = [
                dado.get("titulo", "Dado relevante do mês")
                for dado in insumos.dados_estatisticas
            ]

        # 🔥 PRODUTOS / SERVIÇOS EM ALTA
        elif slug == "produtos_servicos_alta":
            intro = (
                f"🔥 Produtos e serviços que estão em alta neste mês. "
                f"Você pode usar essas ideias para criar conteúdo, "
                f"ofertas e combos estratégicos."
            )

            temas_reais = insumos.produtos_em_alta

        # 🏷️ PROMOÇÕES E OFERTAS
        elif slug == "promocoes_ofertas":
            intro = (
                f"🏷️ Formatos de promoções que fazem sentido para este mês. "
                f"O foco é gerar demanda sem desvalorizar seu produto ou serviço."
            )

            temas_reais = insumos.promocoes_ofertas

        # 🧠 BRANDING E POSICIONAMENTO
        elif slug == "branding_posicionamento":
            intro = (
                f"🧠 Ajustes de branding e posicionamento para este mês. "
                f"Pequenas mudanças que aumentam percepção de valor."
            )

            temas_reais = insumos.branding_posicionamento

        # 🏆 PROVA SOCIAL E AUTORIDADE
        elif slug == "prova_social_autoridade":
            intro = (
                f"🏆 Ideias para mostrar resultado, bastidores e confiança. "
                f"Use isso para fortalecer sua autoridade sem parecer forçado."
            )

            temas_reais = insumos.prova_social_autoridade

        # 🤝 RELACIONAMENTO E COMUNIDADE
        else:
            intro = (
                f"🤝 Conteúdos para gerar conversa, engajamento e vínculo "
                f"com sua audiência ao longo do mês."
            )

            temas_reais = insumos.relacionamento_comunidade

        # 🔢 Quantidade dinâmica de cards
        temas_reais = [t for t in temas_reais if t and t.strip()]
        qtd = max(3, min(len(temas_reais), 10)) if temas_reais else 3
        temas_cards = temas_reais[:qtd] if temas_reais else [tema_base]

        # 🎯 Geração dos conteúdos (AGORA COM TEMA REAL)
        conteudos = []
        for i, tema_real in enumerate(temas_cards, start=1):
            dado_texto = ""
            dado_fonte = ""

            if slug == "dados_estatisticas" and i <= len(insumos.dados_estatisticas):
                dado_texto = insumos.dados_estatisticas[i - 1].get("texto", "")
                dado_fonte = insumos.dados_estatisticas[i - 1].get("fonte", "")


            conteudos.append(
                _gerar_item_conteudo_real(
                    rng=rng,
                    empresa_nome=empresa_nome,
                    nicho=nicho,
                    tema_real=tema_real,
                    numero=i,
                    mes_ano=mes_ano,
                    dado_texto=dado_texto,
                    dado_fonte=dado_fonte,
                )
            )



        # 🧠 Branding complementar (continua como você pediu)
        branding_qtd = min(3, max(2, len(conteudos) // 4))
        branding = [
            _gerar_dica_branding(rng, tema_base, i)
            for i in range(1, branding_qtd + 1)
        ]

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

    # 1) tenta achar antes (rápido)
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

    # 2) protege contra UniqueViolation (uq_consultor_mensal)
    try:
        db.add(reg)
        db.commit()
        db.refresh(reg)
        return {"status": "ok", "conteudo": reg.conteudo}
    except IntegrityError:
        db.rollback()
        reg_existente = db.query(ConsultorMensal).filter(
            ConsultorMensal.usuario_id == usuario_id,
            ConsultorMensal.empresa_id == empresa_id,
            ConsultorMensal.mes_ano == mes_ano
        ).first()
        if reg_existente:
            return {"status": "ok", "conteudo": reg_existente.conteudo, "mensagem": "Já existe consultoria para este mês."}
        raise HTTPException(status_code=500, detail="Erro ao gerar consultoria (conflito de unicidade).")


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

    try:
        db.commit()
        db.refresh(reg)
        return {"status": "ok", "conteudo": reg.conteudo}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao regerar consultoria (conflito de unicidade).")
