from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from pathlib import Path
import os
import json
import httpx
import time
from typing import Any, Dict, List, Optional

router = APIRouter()

# Diretórios base
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_DIR = BACKEND_DIR.parent                     # raiz do projeto

CAMINHO_HISTORICO = PROJECT_DIR / "memory" / "mark.json"
CAMINHO_INSTRUCOES = BACKEND_DIR / "comandos" / "mark_instrucoes.txt"
CAMINHO_PERFIL = PROJECT_DIR / "memory" / "perfil_matheus.json"

CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY não definida.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Modelo padrão do MARK (pode trocar no .env com MARK_MODEL=...)
MARK_MODEL_DEFAULT = os.getenv("MARK_MODEL", "gpt-4o-mini")

# Endpoint interno com os dados da empresa (já existe no seu sistema)
EMPRESA_MARK_URL = os.getenv("EMPRESA_MARK_URL", "http://127.0.0.1:8000/empresa_mark")


class EntradaMARK(BaseModel):
    mensagem: str
    usuario_id: Optional[int] = None
    provedor: Optional[str] = None
    modelo: Optional[str] = None


class EntradaSimples(BaseModel):
    mensagem: str


# ---------------------- Auxiliares ----------------------


def carregar_instrucoes_mark() -> str:
    """Lê o arquivo mark_instrucoes.txt ou usa um fallback padrão."""
    if CAMINHO_INSTRUCOES.exists():
        try:
            texto = CAMINHO_INSTRUCOES.read_text(encoding="utf-8").strip()
            if texto:
                return texto
        except Exception:
            pass
    return (
        "Você é o MARK, consultor de Marketing Digital, Branding e Estratégia de Negócios "
        "criado pela MivCast. Responda sempre em português do Brasil, de forma prática, "
        "direta, estratégica e personalizada para a realidade da empresa do usuário."
    )


def carregar_perfil_matheus() -> Optional[Dict[str, Any]]:
    """Carrega o perfil do Matheus, se existir."""
    if not CAMINHO_PERFIL.exists():
        return None
    try:
        return json.loads(CAMINHO_PERFIL.read_text(encoding="utf-8"))
    except Exception:
        return None


def filtrar_dados_empresa(empresa_bruta: Any) -> Dict[str, Any]:
    """
    Limpa / resume os dados da empresa para não mandar lixo desnecessário para a IA.
    Remove base64 de logo e reduz listas muito grandes.
    """
    if isinstance(empresa_bruta, list):
        if not empresa_bruta:
            return {}
        empresa = dict(empresa_bruta[0])
    elif isinstance(empresa_bruta, dict):
        empresa = dict(empresa_bruta)
    else:
        return {}

    # Evitar mandar base64 gigante da logo
    logo = empresa.get("logo_url")
    if isinstance(logo, str) and logo.startswith("data:image"):
        empresa["logo_url"] = "[logo em base64 removida para otimizar a IA]"

    # Simplificar funcionários
    if isinstance(empresa.get("funcionarios"), list):
        empresa["funcionarios"] = [
            {"nome": f.get("nome"), "cargo": f.get("cargo")}
            for f in empresa["funcionarios"]
            if isinstance(f, dict)
        ]

    # Simplificar produtos
    if isinstance(empresa.get("produtos"), list):
        empresa["produtos"] = [
            {"nome": p.get("nome"), "categoria": p.get("categoria")}
            for p in empresa["produtos"]
            if isinstance(p, dict)
        ]

    return empresa


def carregar_historico() -> List[Dict[str, str]]:
    """Lê o histórico mark.json (para dar contexto)."""
    if not CAMINHO_HISTORICO.exists():
        return []
    try:
        return json.loads(CAMINHO_HISTORICO.read_text(encoding="utf-8"))
    except Exception:
        return []


def salvar_historico(historico: List[Dict[str, str]]) -> None:
    """Salva o histórico no disco (limitando tamanho)."""
    try:
        CAMINHO_HISTORICO.write_text(
            json.dumps(historico, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def montar_mensagens_base(texto: str, usuario_id: Optional[int]) -> List[Dict[str, str]]:
    """
    Monta TODA a lista de mensagens que será enviada para a IA:
    - instruções do MARK
    - perfil do Matheus
    - dados da empresa
    - pequeno histórico
    - pergunta atual
    """
    mensagens: List[Dict[str, str]] = []

    # 1) Instrução principal do MARK
    instrucao = carregar_instrucoes_mark()
    mensagens.append({"role": "system", "content": instrucao})

    # 2) Perfil do Matheus
    perfil = carregar_perfil_matheus()
    if perfil:
        mensagens.append({
            "role": "system",
            "content": (
                "Informações sobre o criador do sistema (Matheus Nascimento). "
                "Use isso para alinhar o estilo de linguagem e o tipo de estratégia sugerida.\n"
                f"{json.dumps(perfil, ensure_ascii=False, indent=2)}"
            ),
        })

    # 3) Dados da empresa (via /empresa_mark)
    try:
        params = {}
        if usuario_id is not None:
            params["usuario_id"] = usuario_id
        r = httpx.get(EMPRESA_MARK_URL, params=params, timeout=5.0)
        if r.status_code == 200:
            empresa = filtrar_dados_empresa(r.json())
        else:
            empresa = {"erro": f"Não foi possível obter dados da empresa (status {r.status_code})."}
    except Exception as e:
        empresa = {"erro": f"Falha ao conectar na API interna de empresa: {e}"}

    mensagens.append({
        "role": "system",
        "content": (
            "Dados reais da empresa do usuário. Use SEMPRE essas informações para personalizar a resposta. "
            "Se algo estiver vazio, faça perguntas de diagnóstico antes de sugerir ações.\n"
            f"{json.dumps(empresa, ensure_ascii=False, indent=2)}"
        ),
    })

    # 4) Pequeno histórico anterior (apenas as últimas interações)
    historico = carregar_historico()
    for item in historico[-5:]:
        p = item.get("pergunta")
        r = item.get("resposta")
        if p and r:
            mensagens.append({"role": "user", "content": p})
            mensagens.append({"role": "assistant", "content": r})

    # 5) Pergunta atual
    mensagens.append({"role": "user", "content": texto})
    return mensagens


async def chamar_openai(mensagens: List[Dict[str, str]], modelo: Optional[str] = None) -> str:
    """Chamada padrão (não streaming) para a OpenAI."""
    modelo_usado = modelo or MARK_MODEL_DEFAULT
    inicio = time.monotonic()
    try:
        resposta = await client.chat.completions.create(
            model=modelo_usado,
            messages=mensagens,
            temperature=0.4,
            timeout=30,
        )
        conteudo = resposta.choices[0].message.content or ""
    except Exception as e:
        conteudo = f"Erro ao gerar resposta com IA: {e}"
    fim = time.monotonic()
    print(f"[MARK] Modelo: {modelo_usado} | Tempo OpenAI: {fim - inicio:.2f}s")
    return conteudo.strip()


# ---------------------- Endpoints ----------------------


@router.post("/responder")
async def responder_mark(entrada: EntradaMARK):
    """
    Endpoint tradicional, que retorna a resposta inteira em JSON.
    Ainda é usado pelo sistema (e pode servir de fallback).
    """
    texto = (entrada.mensagem or "").strip()
    if not texto:
        return {"resposta": "Me envie uma pergunta ou contexto para que eu possa te ajudar."}

    mensagens = montar_mensagens_base(texto, entrada.usuario_id)
    resposta_texto = await chamar_openai(mensagens, entrada.modelo)

    historico = carregar_historico()
    if not resposta_texto.startswith("Erro ao gerar resposta com IA"):
        historico.append({"pergunta": texto, "resposta": resposta_texto})
        if len(historico) > 50:
            historico = historico[-50:]
        salvar_historico(historico)

    return {"resposta": resposta_texto}


@router.post("/stream")
async def stream_mark(entrada: EntradaMARK):
    """
    Endpoint com STREAMING de tokens.
    O front (Streamlit) vai consumir isso em tempo real.
    """
    texto = (entrada.mensagem or "").strip()
    if not texto:
        async def gen_vazio():
            yield "Me envie uma pergunta ou contexto para que eu possa te ajudar."
        return StreamingResponse(gen_vazio(), media_type="text/plain; charset=utf-8")

    mensagens = montar_mensagens_base(texto, entrada.usuario_id)
    modelo_usado = entrada.modelo or MARK_MODEL_DEFAULT

    async def token_generator():
        full = ""
        inicio = time.monotonic()
        try:
            stream = await client.chat.completions.create(
                model=modelo_usado,
                messages=mensagens,
                temperature=0.4,
                timeout=60,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full += delta
                    # envia só o pedaço novo
                    yield delta
        except Exception as e:
            err = f"\n[ERRO IA] {e}"
            yield err
        fim = time.monotonic()
        print(f"[MARK][STREAM] Modelo: {modelo_usado} | Tempo OpenAI: {fim - inicio:.2f}s")

        # salvar no histórico ao final
        if full and not full.startswith("Erro ao gerar resposta com IA"):
            historico = carregar_historico()
            historico.append({"pergunta": texto, "resposta": full})
            if len(historico) > 50:
                historico = historico[-50:]
            salvar_historico(historico)

    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")


@router.post("/responder_simples")
async def responder_simples(entrada: EntradaSimples):
    """
    Endpoint de teste rápido (sem perfil, sem empresa).
    Útil pra medir velocidade da OpenAI pura.
    """
    texto = (entrada.mensagem or "").strip()
    if not texto:
        return {"resposta": "Envie uma mensagem para teste."}

    mensagens = [
        {
            "role": "system",
            "content": "Você é o MARK, um assistente de testes. Responda em português do Brasil de forma curta.",
        },
        {"role": "user", "content": texto},
    ]
    resposta_texto = await chamar_openai(mensagens)
    return {"resposta": resposta_texto}
