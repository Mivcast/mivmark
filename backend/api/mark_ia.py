from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

import os
import json
import time

from backend.database import get_db
from backend.models import Empresa

router = APIRouter()

# ---------------------------------------------------------
# CAMINHOS (iguais ao padrão antigo do MARK) :contentReference[oaicite:0]{index=0}
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
PROJECT_DIR = BACKEND_DIR.parent                     # raiz do projeto

CAMINHO_HISTORICO = PROJECT_DIR / "memory" / "mark.json"
CAMINHO_INSTRUCOES = BACKEND_DIR / "comandos" / "mark_instrucoes.txt"
CAMINHO_PERFIL = PROJECT_DIR / "memory" / "perfil_matheus.json"

CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# OPENAI CLIENT :contentReference[oaicite:1]{index=1}
# ---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY não definida.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MARK_MODEL_DEFAULT = os.getenv("MARK_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------
# MODELOS Pydantic (mantidos compatíveis) :contentReference[oaicite:2]{index=2}
# ---------------------------------------------------------
class EntradaMARK(BaseModel):
    mensagem: str
    usuario_id: Optional[int] = None
    provedor: Optional[str] = None
    modelo: Optional[str] = None


class EntradaSimples(BaseModel):
    mensagem: str


# ---------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------
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


def empresa_to_dict(empresa: Empresa) -> Dict[str, Any]:
    """Converte o modelo Empresa em dict simples."""
    if not empresa:
        return {}

    return {
        "id": getattr(empresa, "id", None),
        "usuario_id": getattr(empresa, "usuario_id", None),
        "nome_empresa": getattr(empresa, "nome_empresa", None),
        "descricao": getattr(empresa, "descricao", None),
        "nicho": getattr(empresa, "nicho", None),
        "logo_url": getattr(empresa, "logo_url", None),
        "funcionarios": getattr(empresa, "funcionarios", None),
        "produtos": getattr(empresa, "produtos", None),
        "redes_sociais": getattr(empresa, "redes_sociais", None),
        "informacoes_adicionais": getattr(empresa, "informacoes_adicionais", None),
        "cnpj": getattr(empresa, "cnpj", None),
        "rua": getattr(empresa, "rua", None),
        "numero": getattr(empresa, "numero", None),
        "bairro": getattr(empresa, "bairro", None),
        "cidade": getattr(empresa, "cidade", None),
        "cep": getattr(empresa, "cep", None),
        "atualizado_em": (
            empresa.atualizado_em.isoformat()
            if getattr(empresa, "atualizado_em", None)
            else None
        ),
    }


def filtrar_dados_empresa(empresa_bruta: Any) -> Dict[str, Any]:
    """
    Limpa / resume os dados da empresa para não mandar lixo desnecessário para a IA.
    (versão adaptada do código antigo). :contentReference[oaicite:3]{index=3}
    """
    if not empresa_bruta:
        return {}

    if isinstance(empresa_bruta, dict):
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
            {"nome": f.get("nome"), "funcao": f.get("funcao")}
            for f in empresa["funcionarios"]
            if isinstance(f, dict)
        ]

    # Simplificar produtos
    if isinstance(empresa.get("produtos"), list):
        empresa["produtos"] = [
            {"nome": p.get("nome"), "preco": p.get("preco")}
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


def obter_empresa_do_usuario(db: Session, usuario_id: Optional[int]) -> Dict[str, Any]:
    """
    Busca a empresa vinculada ao usuário.
    Se usuario_id for None ou não tiver empresa, tenta pegar a mais recente. :contentReference[oaicite:4]{index=4}
    """
    query = db.query(Empresa)

    if usuario_id is not None:
        query = query.filter(Empresa.usuario_id == usuario_id)

    empresa = query.order_by(Empresa.atualizado_em.desc()).first()
    if not empresa:
        return {}

    return filtrar_dados_empresa(empresa_to_dict(empresa))


def montar_mensagens_base(
    texto: str, usuario_id: Optional[int], db: Session
) -> List[Dict[str, str]]:
    """
    Monta TODA a lista de mensagens que será enviada para a IA:
    - instruções do MARK
    - perfil do Matheus
    - dados da empresa (via banco)
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
        mensagens.append(
            {
                "role": "system",
                "content": (
                    "Informações sobre o criador do sistema (Matheus Nascimento). "
                    "Use isso para alinhar o estilo de linguagem e o tipo de estratégia sugerida.\n"
                    f"{json.dumps(perfil, ensure_ascii=False, indent=2)}"
                ),
            }
        )

    # 3) Dados da empresa (via banco, não mais via /empresa_mark)
    empresa = obter_empresa_do_usuario(db, usuario_id)
    if empresa:
        conteudo_empresa = (
            "Dados reais da empresa do usuário. Use SEMPRE essas informações para personalizar a resposta. "
            "Se algo estiver vazio, faça perguntas de diagnóstico antes de sugerir ações.\n"
            f"{json.dumps(empresa, ensure_ascii=False, indent=2)}"
        )
    else:
        conteudo_empresa = (
            "ATENÇÃO: o sistema NÃO localizou dados de empresa para este usuário.\n"
            "Explique isso de forma educada ao usuário e oriente a preencher o módulo 'Empresa' "
            "no sistema MivMark para que você consiga personalizar melhor as respostas. "
            "Enquanto isso, responda de forma mais genérica, sem inventar dados."
        )

    mensagens.append({"role": "system", "content": conteudo_empresa})

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


async def chamar_openai(
    mensagens: List[Dict[str, str]], modelo: Optional[str] = None
) -> str:
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


# ---------------------------------------------------------
# ENDPOINTS PRINCIPAIS (compatíveis com versão antiga) :contentReference[oaicite:5]{index=5}
# ---------------------------------------------------------
@router.post("/responder")
async def responder_mark(entrada: EntradaMARK, db: Session = Depends(get_db)):
    """
    Endpoint tradicional, que retorna a resposta inteira em JSON.
    Ainda é usado pelo sistema (e pode servir de fallback).
    """
    texto = (entrada.mensagem or "").strip()
    if not texto:
        return {"resposta": "Me envie uma pergunta ou contexto para que eu possa te ajudar."}

    mensagens = montar_mensagens_base(texto, entrada.usuario_id, db)
    resposta_texto = await chamar_openai(mensagens, entrada.modelo)

    historico = carregar_historico()
    if not resposta_texto.startswith("Erro ao gerar resposta com IA"):
        historico.append({"pergunta": texto, "resposta": resposta_texto})
        if len(historico) > 50:
            historico = historico[-50:]
        salvar_historico(historico)

    return {"resposta": resposta_texto}


@router.post("/stream")
async def stream_mark(entrada: EntradaMARK, db: Session = Depends(get_db)):
    """
    Endpoint com STREAMING de tokens.
    O front (HTML/Streamlit) consome isso em tempo real.
    """
    texto = (entrada.mensagem or "").strip()
    if not texto:

        async def gen_vazio():
            yield "Me envie uma pergunta ou contexto para que eu possa te ajudar."

        return StreamingResponse(gen_vazio(), media_type="text/plain; charset=utf-8")

    mensagens = montar_mensagens_base(texto, entrada.usuario_id, db)
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
