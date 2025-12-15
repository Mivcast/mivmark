# backend/services/inteligencia_mercado.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# Onde você pode guardar insumos “reais/curados” por mês e nicho.
# Ex.: backend/data/insumos/2025-12.json
BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
INSUMOS_DIR = BASE_DIR / "data" / "insumos"


@dataclass
class MarketIntel:
    mes_ano: str
    nicho: str

    tendencias: List[str]
    dados_estatisticas: List[Dict[str, str]]  # {"titulo": "...", "texto": "...", "fonte": "..."}
    produtos_em_alta: List[str]
    promocoes_ofertas: List[str]
    branding_posicionamento: List[str]
    prova_social_autoridade: List[str]
    relacionamento_comunidade: List[str]

    # extras úteis para o consultor montar melhor os cards
    observacoes: List[str]


def _normalizar_nicho(nicho: str) -> str:
    return (nicho or "").strip().lower()


def _carregar_json_mes(mes_ano: str) -> Optional[Dict[str, Any]]:
    """
    Tenta carregar insumos curados do disco:
    backend/data/insumos/<mes_ano>.json
    """
    caminho = INSUMOS_DIR / f"{mes_ano}.json"
    if not caminho.exists():
        return None

    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_mes(mes_ano: str) -> str:
    if "-" in mes_ano:
        return mes_ano.split("-")[1]
    return ""


def _fallback_por_mes(mes_ano: str, nicho: str) -> MarketIntel:
    """
    Fallback “concreto” por mês (sem prometer ser pesquisa externa).
    Serve para o sistema nunca ficar genérico demais.
    Você pode enriquecer esse fallback aos poucos.
    """
    mes = _get_mes(mes_ano)
    nicho_norm = _normalizar_nicho(nicho)

    # Defaults gerais (concretos e aplicáveis)
    tendencias = []
    produtos = []
    promocoes = []
    branding = []
    prova = []
    comunidade = []
    dados = []
    obs = []

    if mes == "12":
        obs.append("Dezembro tende a concentrar picos de intenção de compra e busca por praticidade (fim de ano).")

        # Tendências gerais do mês (aplicáveis, não “genéricas”)
        tendencias += [
            "Conteúdo de ‘kit pronto’/‘pacote especial’ para o fim de ano (praticidade)",
            "Posts curtos com “lista rápida” (3–5 itens) para decisões de compra",
            "Reels de bastidores e produção (cresce confiança antes da compra)",
            "Combos e ofertas por tempo limitado até o dia 31",
        ]

        produtos += [
            "Kits/combos temáticos de fim de ano (presentes, confraternização, ceia)",
            "Produtos ‘pronto para usar/consumir’ (praticidade)",
            "Itens premium/edição limitada para presentear",
        ]

        promocoes += [
            "Oferta de ‘última chance’ (contagem regressiva até 31/12)",
            "Combo 2+1 ou ‘leve mais por menos’ para aumentar ticket médio",
            "Brinde condicionado (ex.: acima de R$X ganha Y)",
            "Frete/entrega incentivada para fechar pedido (quando aplicável)",
        ]

        branding += [
            "Repetir a promessa central em todo post (mesma frase final) para fixar a marca",
            "Padronizar um ‘selo’ visual do mês (ex.: ‘Especial Dezembro’) em todos os criativos",
        ]

        prova += [
            "Antes/depois com contexto (situação → solução → resultado) em formato carrossel",
            "Depoimento curto em vídeo (7–12s) + texto na tela + CTA simples",
        ]

        comunidade += [
            "Caixinha de perguntas: ‘Qual sua maior dúvida para o fim de ano?’",
            "Enquete de escolha: ‘Você prefere A ou B?’ e responder nos stories",
        ]

        dados += [
            {
                "titulo": "Dezembro: comportamento típico de compra",
                "texto": "No fim do ano, cresce a busca por praticidade, presentes e decisões rápidas — por isso listas curtas e combos tendem a performar bem.",
                "fonte": "Observação de mercado (heurística do sistema)",
            }
        ]

    # Personalização por nicho (exemplo forte: alimentos veganos)
    if "veg" in nicho_norm or "vegano" in nicho_norm:
        if mes == "12":
            tendencias = [
                "Ceia vegana prática (receitas rápidas e poucos ingredientes)",
                "Sobremesas veganas ‘premium’ para festas (apelo de presente/compartilhar)",
                "Reels de montagem rápida (antes/depois do prato em 8–12s)",
                "Conteúdo educativo: ‘como substituir X por Y’ sem perder sabor",
            ]

            produtos = [
                "Kit ‘Ceia Vegana’ (entrada + principal + sobremesa)",
                "Sobremesas veganas (chocolate amargo vegano, tortas, frutas elaboradas)",
                "Pratos principais mais procurados no fim de ano (risoto de cogumelos, lentilha, assados vegetais)",
            ]

            promocoes = [
                "Combo ‘Ceia Completa’ com desconto progressivo (quanto mais itens, maior o desconto)",
                "Reserva antecipada até data limite (ex.: até dia 20) com benefício",
                "Entrega agendada para 24/12 e 31/12 (valor percebido alto)",
            ]

            dados = [
                {
                    "titulo": "Dezembro no nicho vegano: o que tende a funcionar",
                    "texto": "Conteúdos de ceia e praticidade costumam engajar mais no fim do ano — especialmente com listas e passo a passo curto.",
                    "fonte": "Observação de mercado (heurística do sistema)",
                }
            ]

    return MarketIntel(
        mes_ano=mes_ano,
        nicho=nicho,
        tendencias=tendencias,
        dados_estatisticas=dados,
        produtos_em_alta=produtos,
        promocoes_ofertas=promocoes,
        branding_posicionamento=branding,
        prova_social_autoridade=prova,
        relacionamento_comunidade=comunidade,
        observacoes=obs,
    )


def obter_insumos(mes_ano: str, nicho: str) -> MarketIntel:
    """
    Retorna insumos para o mês e nicho.
    Prioridade:
    1) JSON curado (backend/data/insumos/<mes_ano>.json)
    2) fallback por mês + nicho (heurística)
    """
    nicho_norm = _normalizar_nicho(nicho)
    data_mes = _carregar_json_mes(mes_ano)

    if isinstance(data_mes, dict):
        # Estrutura esperada:
        # {
        #   "default": {...},
        #   "nichos": {
        #       "alimentos veganos": {...}
        #   }
        # }
        bloco_default = data_mes.get("default") or {}
        bloco_nichos = data_mes.get("nichos") or {}

        escolhido = None
        if isinstance(bloco_nichos, dict):
            # tenta match simples por chave
            for k, v in bloco_nichos.items():
                if _normalizar_nicho(k) == nicho_norm:
                    escolhido = v
                    break

        # merge: nicho sobrepõe default
        merged = dict(bloco_default)
        if isinstance(escolhido, dict):
            merged.update(escolhido)

        return MarketIntel(
            mes_ano=mes_ano,
            nicho=nicho,
            tendencias=list(merged.get("tendencias", []) or []),
            dados_estatisticas=list(merged.get("dados_estatisticas", []) or []),
            produtos_em_alta=list(merged.get("produtos_em_alta", []) or []),
            promocoes_ofertas=list(merged.get("promocoes_ofertas", []) or []),
            branding_posicionamento=list(merged.get("branding_posicionamento", []) or []),
            prova_social_autoridade=list(merged.get("prova_social_autoridade", []) or []),
            relacionamento_comunidade=list(merged.get("relacionamento_comunidade", []) or []),
            observacoes=list(merged.get("observacoes", []) or []),
        )

    return _fallback_por_mes(mes_ano, nicho)
