from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI
import os, json, httpx
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------
# CONFIGURAÇÕES DE CAMINHO (BASEADO NO LOCAL DESTE ARQUIVO)
# ---------------------------------------------------------------------
# .../mivmark/backend/api/mark_ia.py  -> root = .../mivmark
ROOT_DIR = Path(__file__).resolve().parents[2]
MEMORY_DIR = ROOT_DIR / "memory"

CAMINHO_HISTORICO = MEMORY_DIR / "mark.json"
CAMINHO_PERFIL = MEMORY_DIR / "perfil_matheus.json"
CAMINHO_INSTRUCOES = ROOT_DIR / "backend" / "comandos" / "mark_instrucoes.txt"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

# ---------------------------------------------------------------------
# MODELO DE ENTRADA
# ---------------------------------------------------------------------
class EntradaMARK(BaseModel):
    mensagem: str
    usuario_id: int | None = None
    provedor: str | None = None   # "openai" (padrão), "deepseek", etc.
    modelo: str | None = None     # "gpt-4o-mini", "gpt-4o", etc.


# ---------------------------------------------------------------------
# CLIENTE OPENAI
# ---------------------------------------------------------------------
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)


async def chamar_ia(mensagens, provedor: str = "openai", modelo: str | None = None) -> str:
    """
    Função central para falar com a IA.
    Hoje só está implementado OPENAI.
    Estrutura pronta para adicionar outros provedores no futuro.
    """
    provedor = (provedor or "openai").lower()

    # ---------------------- OPENAI (PADRÃO) ----------------------
    if provedor == "openai":
        client = get_openai_client()
        if not client:
            return "Erro: OPENAI_API_KEY não configurada no servidor."

        modelo_padrao = os.getenv("MARK_MODEL", "gpt-4o-mini")
        modelo_usado = modelo or modelo_padrao

        try:
            resposta = await client.chat.completions.create(
                model=modelo_usado,
                messages=mensagens,
                temperature=0.4,
                timeout=45,
            )
            return resposta.choices[0].message.content.strip()

        except Exception as e:
            erro = str(e)
            if "invalid_api_key" in erro.lower():
                return "Erro: chave da OpenAI inválida ou expirada."
            return f"Erro ao gerar resposta com a IA (OpenAI): {erro}"

    # ---------------------- PROVEDORES FUTUROS -------------------
    if provedor == "deepseek":
        return "Suporte a DeepSeek ainda não implementado. Estrutura pronta no backend."

    return f"Erro: provedor de IA '{provedor}' não é suportado no momento."


# ---------------------------------------------------------------------
# ROTA PRINCIPAL DO MARK IA
# ---------------------------------------------------------------------
@router.post("/responder")
async def responder_mark(entrada: EntradaMARK):
    texto = entrada.mensagem.strip()
    mensagens: list[dict] = []

    # ==============================================================
    # 1) INSTRUÇÕES PRINCIPAIS DO MARK (SYSTEM)
    # ==============================================================
    if CAMINHO_INSTRUCOES.exists():
        try:
            conteudo_instrucao = CAMINHO_INSTRUCOES.read_text(encoding="utf-8").strip()
            if conteudo_instrucao:
                mensagens.append({"role": "system", "content": conteudo_instrucao})
        except Exception as e:
            mensagens.append({
                "role": "system",
                "content": f"Não foi possível carregar mark_instrucoes.txt (erro: {e}). "
                           f"Aja como consultor de marketing da MivCast e responda normalmente."
            })

    # ==============================================================
    # 2) RESUMO INTELIGENTE DOS DADOS DA EMPRESA (SYSTEM)
    # ==============================================================
    empresa = {}
    try:
        r = httpx.get("http://127.0.0.1:8000/empresa_mark")
        if r.status_code == 200:
            data = r.json()
            # Se vier lista, pega a primeira empresa
            if isinstance(data, list) and data:
                empresa = data[0]
            else:
                empresa = data
        else:
            empresa = {"erro": f"Erro ao buscar dados da empresa (MARK): {r.status_code} - {r.text}"}
    except Exception as e:
        empresa = {"erro": f"Falha ao acessar /empresa_mark: {e}"}

    if isinstance(empresa, dict) and not empresa.get("erro"):
        nome = (
            empresa.get("nome_empresa")
            or empresa.get("nome_fantasia")
            or empresa.get("nome")
            or "Empresa do usuário"
        )
        nicho = (
            empresa.get("nicho")
            or empresa.get("segmento")
            or empresa.get("ramo")
            or "não informado"
        )
        cidade = empresa.get("cidade") or ""
        cep = empresa.get("cep") or ""

        resumo_empresa = f"""
A empresa do usuário cadastrada no sistema é:

• Nome da empresa: {nome}
• Segmento / Nicho: {nicho}
• Localização (cidade / CEP): {cidade} {cep}

Use EXATAMENTE esse nome e esse nicho ao falar sobre a empresa do usuário,
mesmo que outras instruções mencionem o nome "MivCast" como agência criadora.

Dados completos retornados pelo backend (JSON):
{json.dumps(empresa, indent=2, ensure_ascii=False)}
"""
    else:
        resumo_empresa = f"""
Não foi possível carregar dados estruturados da empresa do usuário.
Conteúdo retornado:
{json.dumps(empresa, indent=2, ensure_ascii=False)}
Responda de forma genérica, mas avise que os dados da empresa não foram encontrados.
"""

    mensagens.append({"role": "system", "content": resumo_empresa})

    # ==============================================================
    # 3) PERFIL DO CRIADOR (opcional)
    # ==============================================================
    if CAMINHO_PERFIL.exists():
        try:
            perfil = json.loads(CAMINHO_PERFIL.read_text(encoding="utf-8"))
            mensagens.append({
                "role": "user",
                "content": f"Perfil do criador do sistema (Matheus):\n"
                           f"{json.dumps(perfil, indent=2, ensure_ascii=False)}"
            })
        except Exception as e:
            mensagens.append({
                "role": "system",
                "content": f"Não foi possível carregar perfil_matheus.json (erro: {e})."
            })

    # ==============================================================
    # 4) DADOS COMPLEMENTARES (consultoria / marketing)
    # ==============================================================
    texto_baixo = texto.lower()
    extras = ""

    # Progresso da consultoria
    if "consultoria" in texto_baixo or "análise" in texto_baixo:
        try:
            r = httpx.get("http://127.0.0.1:8000/consultoria/progresso")
            if r.status_code == 200:
                progresso = r.json()
                concluidos = sum(1 for t in progresso.values() if t.get("concluido"))
                total = len(progresso)
                extras += f"\n📊 Progresso da consultoria: {concluidos}/{total} tópicos concluídos."
        except Exception:
            pass

    # Cards de marketing
    if "marketing" in texto_baixo or "campanha" in texto_baixo or "promoção" in texto_baixo:
        mes = date.today().strftime("%Y-%m")
        try:
            r = httpx.get(f"http://127.0.0.1:8000/marketing/cards/{mes}")
            if r.status_code == 200:
                cards = r.json()
                lista = "\n".join([f"• {c.get('titulo', 'Sem título')}" for c in cards[:5]])
                extras += f"\n📣 Principais cards de marketing do mês:\n{lista}"
        except Exception:
            pass

    if extras:
        mensagens.append({"role": "assistant", "content": extras})

    # ==============================================================
    # 5) HISTÓRICO CURTO (apenas 3 interações)
    # ==============================================================
    historico = []
    if CAMINHO_HISTORICO.exists():
        try:
            historico = json.loads(CAMINHO_HISTORICO.read_text(encoding="utf-8"))
        except Exception:
            historico = []

        for item in historico[-3:]:
            perg = item.get("pergunta", "")
            resp = item.get("resposta", "")
            if perg:
                mensagens.append({"role": "user", "content": perg})
            if resp:
                mensagens.append({"role": "assistant", "content": resp})

    # ==============================================================
    # 6) PERGUNTA ATUAL DO USUÁRIO
    # ==============================================================
    if texto:
        mensagens.append({"role": "user", "content": texto})

    # ==============================================================
    # 7) CHAMAR A IA
    # ==============================================================
    conteudo = await chamar_ia(
        mensagens,
        provedor=entrada.provedor or "openai",
        modelo=entrada.modelo
    )

    # ==============================================================
    # 8) SALVAR NO HISTÓRICO
    # ==============================================================
    if texto and not conteudo.startswith("Erro"):
        historico.append({"pergunta": texto, "resposta": conteudo})
        CAMINHO_HISTORICO.write_text(
            json.dumps(historico, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    return {"resposta": conteudo}
