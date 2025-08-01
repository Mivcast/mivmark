from fastapi import APIRouter
from openai import AsyncOpenAI
from pydantic import BaseModel
import os, json, httpx
from datetime import date

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CAMINHO_HISTORICO = os.path.join("memory", "mark.json")
CAMINHO_INSTRUCOES = os.path.join("comandos", "mark_instrucoes.txt")
CAMINHO_PERFIL = os.path.join("memory", "perfil_matheus.json")

os.makedirs("memory", exist_ok=True)

class EntradaMARK(BaseModel):
    mensagem: str
    usuario_id: int = None

@router.post("/responder")
async def responder_mark(entrada: EntradaMARK):
    texto = entrada.mensagem.strip()
    mensagens = []

    # Instruções do MARK
    if os.path.exists(CAMINHO_INSTRUCOES):
        with open(CAMINHO_INSTRUCOES, "r", encoding="utf-8") as f:
            conteudo_instrucao = f.read().strip()
            if conteudo_instrucao:
                mensagens.append({"role": "system", "content": conteudo_instrucao})

    # Perfil do Matheus
    if os.path.exists(CAMINHO_PERFIL):
        with open(CAMINHO_PERFIL, "r", encoding="utf-8") as f:
            perfil = json.load(f)
            mensagens.append({
                "role": "user",
                "content": f"Perfil do criador:\n{json.dumps(perfil, indent=2, ensure_ascii=False)}"
            })

    # Dados reais da empresa
    empresa = {}
    headers = {"Authorization": f"Bearer {os.getenv('ADMIN_TOKEN')}"}
    try:
        resposta_empresa = httpx.get("http://127.0.0.1:8000/empresa", headers=headers)
        if resposta_empresa.status_code == 200:
            empresa = resposta_empresa.json()
        else:
            empresa = {"erro": f"Erro ao buscar dados: {resposta_empresa.status_code}"}
    except Exception as e:
        empresa = {"erro": f"Erro ao buscar dados reais da empresa: {e}"}

    mensagens.append({
        "role": "user",
        "content": f"Dados reais da empresa do usuário:\n{json.dumps(empresa, indent=2, ensure_ascii=False)}"
    })

    # Detectar intenção com base na mensagem
    texto_baixo = texto.lower()
    resposta_extra = ""

    if "consultoria" in texto_baixo or "análise da empresa" in texto_baixo:
        try:
            r = httpx.get("http://127.0.0.1:8000/consultoria/progresso", headers=headers)
            if r.status_code == 200:
                progresso = r.json()
                concluidos = sum(1 for t in progresso.values() if t.get("concluido"))
                total = len(progresso)
                resposta_extra += f"\n📊 Progresso da Consultoria: {concluidos}/{total} tópicos concluídos."
            else:
                resposta_extra += "\n⚠️ Não foi possível obter o progresso da consultoria."
        except Exception as e:
            resposta_extra += f"\nErro ao buscar dados da consultoria: {e}"

    if "campanha" in texto_baixo or "marketing" in texto_baixo or "promoção" in texto_baixo:
        mes_atual = date.today().strftime("%Y-%m")
        try:
            r = httpx.get(f"http://127.0.0.1:8000/marketing/cards/{mes_atual}", headers=headers)
            if r.status_code == 200:
                cards = r.json()
                resumo = "\n".join([f"📌 {c['titulo']}" for c in cards[:5]])
                resposta_extra += f"\n📣 Cards de Marketing em {mes_atual}:\n{resumo}"
            else:
                resposta_extra += "\n⚠️ Não foi possível obter os cards de marketing."
        except Exception as e:
            resposta_extra += f"\nErro ao buscar dados de marketing: {e}"

    if resposta_extra:
        mensagens.append({
            "role": "user",
            "content": f"Dados complementares para ajudar na resposta:\n{resposta_extra}"
        })

    # Histórico recente
    historico = []
    if os.path.exists(CAMINHO_HISTORICO):
        with open(CAMINHO_HISTORICO, "r", encoding="utf-8") as f:
            historico = json.load(f)
        for item in historico[-5:]:
            if "pergunta" in item and "resposta" in item:
                mensagens.append({"role": "user", "content": item["pergunta"]})
                mensagens.append({"role": "assistant", "content": item["resposta"]})

    if texto:
        mensagens.append({"role": "user", "content": texto})

    # Chamada à IA
    try:
        resposta = await client.chat.completions.create(
            model="gpt-4",
            messages=mensagens,
            temperature=0.5,
            timeout=120
        )
        conteudo = resposta.choices[0].message.content.strip()
    except Exception as e:
        conteudo = f"Erro ao gerar resposta com IA: {e}"

    # Salva no histórico
    if texto and not conteudo.startswith("Erro ao gerar resposta"):
        historico.append({"pergunta": texto, "resposta": conteudo})
        with open(CAMINHO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)

    return {"resposta": conteudo}
