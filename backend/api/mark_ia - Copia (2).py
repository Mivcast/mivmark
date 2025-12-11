from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import os
import json
from datetime import datetime

from backend.database import get_db
from backend.models import Empresa, HistoricoMark

router = APIRouter()

# ---------------------------------------------------------
# CAMINHOS
# ---------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent

CAMINHO_HISTORICO = PROJECT_DIR / "memory" / "mark.json"
CAMINHO_INSTRUCOES = BACKEND_DIR / "comandos" / "mark_instrucoes.txt"
CAMINHO_PERFIL = PROJECT_DIR / "memory" / "perfil_matheus.json"

CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# OPENAI CLIENT
# ---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Variável de ambiente OPENAI_API_KEY não definida.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MARK_MODEL_DEFAULT = os.getenv("MARK_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------
# MODELOS Pydantic
# ---------------------------------------------------------
class EntradaMARK(BaseModel):
    mensagem: str
    usuario_id: Optional[int] = None
    provedor: Optional[str] = None
    modelo: Optional[str] = None


class EntradaSimples(BaseModel):
    mensagem: str


class RegistrarHistoricoPayload(BaseModel):
    mensagem: str
    resposta: str
    usuario_id: Optional[int] = None


# ---------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------
def carregar_instrucoes_mark() -> str:
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
    if not CAMINHO_PERFIL.exists():
        return None
    try:
        return json.loads(CAMINHO_PERFIL.read_text(encoding="utf-8"))
    except Exception:
        return None


def empresa_to_dict(empresa: Empresa) -> Dict[str, Any]:
    if not empresa:
        return {}

    return {
        "id": empresa.id,
        "usuario_id": empresa.usuario_id,
        "nome_empresa": empresa.nome_empresa,
        "descricao": empresa.descricao,
        "nicho": empresa.nicho,
        "logo_url": empresa.logo_url,
        "funcionarios": empresa.funcionarios,
        "produtos": empresa.produtos,
        "redes_sociais": empresa.redes_sociais,
        "informacoes_adicionais": empresa.informacoes_adicionais,
        "cnpj": empresa.cnpj,
        "rua": empresa.rua,
        "numero": empresa.numero,
        "bairro": empresa.bairro,
        "cidade": empresa.cidade,
        "cep": empresa.cep,
        "atualizado_em": empresa.atualizado_em.isoformat() if empresa.atualizado_em else None,
    }


def filtrar_dados_empresa(empresa_bruta: Any) -> Dict[str, Any]:
    if not empresa_bruta:
        return {}

    if isinstance(empresa_bruta, dict):
        empresa = dict(empresa_bruta)
    else:
        return {}

    logo = empresa.get("logo_url")
    if isinstance(logo, str) and logo.startswith("data:image"):
        empresa["logo_url"] = "[logo em base64 removida]"

    if isinstance(empresa.get("funcionarios"), list):
        empresa["funcionarios"] = [
            {"nome": f.get("nome"), "funcao": f.get("funcao")}
            for f in empresa["funcionarios"]
            if isinstance(f, dict)
        ]

    if isinstance(empresa.get("produtos"), list):
        empresa["produtos"] = [
            {"nome": p.get("nome"), "preco": p.get("preco")}
            for p in empresa["produtos"]
            if isinstance(p, dict)
        ]

    return empresa


def carregar_historico_json() -> List[Dict[str, str]]:
    if not CAMINHO_HISTORICO.exists():
        return []
    try:
        return json.loads(CAMINHO_HISTORICO.read_text(encoding="utf-8"))
    except Exception:
        return []


def salvar_historico_json(historico: List[Dict[str, str]]) -> None:
    try:
        CAMINHO_HISTORICO.write_text(
            json.dumps(historico, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def obter_empresa_do_usuario(db: Session, usuario_id: Optional[int]) -> Dict[str, Any]:
    query = db.query(Empresa)
    if usuario_id is not None:
        query = query.filter(Empresa.usuario_id == usuario_id)

    empresa = query.order_by(Empresa.atualizado_em.desc()).first()
    if not empresa:
        return {}

    return filtrar_dados_empresa(empresa_to_dict(empresa))


def montar_mensagens_base(texto: str, usuario_id: Optional[int], db: Session) -> List[Dict[str, str]]:
    mensagens: List[Dict[str, str]] = []

    instrucao = carregar_instrucoes_mark()
    mensagens.append({"role": "system", "content": instrucao})

    perfil = carregar_perfil_matheus()
    if perfil:
        mensagens.append(
            {
                "role": "system",
                "content": "Informações do criador:\n" + json.dumps(perfil, ensure_ascii=False),
            }
        )

    empresa = obter_empresa_do_usuario(db, usuario_id)
    if empresa:
        mensagens.append(
            {
                "role": "system",
                "content": "Dados reais da empresa:\n" + json.dumps(empresa, ensure_ascii=False),
            }
        )
    else:
        mensagens.append(
            {
                "role": "system",
                "content": (
                    "Nenhum dado de empresa encontrado para este usuário. "
                    "Peça para preencher o módulo Empresa."
                ),
            }
        )

    historico = carregar_historico_json()
    for item in historico[-5:]:
        mensagens.append({"role": "user", "content": item["pergunta"]})
        mensagens.append({"role": "assistant", "content": item["resposta"]})

    mensagens.append({"role": "user", "content": texto})
    return mensagens


async def chamar_openai(mensagens: List[Dict[str, str]], modelo: Optional[str] = None) -> str:
    modelo_usado = modelo or MARK_MODEL_DEFAULT
    try:
        resposta = await client.chat.completions.create(
            model=modelo_usado,
            messages=mensagens,
            temperature=0.4,
            timeout=30,
        )
        return (resposta.choices[0].message.content or "").strip()
    except Exception as e:
        return (
            "[ERRO IA] Error code: 401 - "
            f"{e}"
        )


# =====================================================================
# 🔥 ENDPOINT /responder — salva JSON + BANCO
# =====================================================================
@router.post("/responder")
async def responder_mark(entrada: EntradaMARK, db: Session = Depends(get_db)):

    texto = (entrada.mensagem or "").strip()
    if not texto:
        return {"resposta": "Envie uma mensagem válida."}

    mensagens = montar_mensagens_base(texto, entrada.usuario_id, db)
    resposta_texto = await chamar_openai(mensagens, entrada.modelo)

    historico = carregar_historico_json()
    historico.append({"pergunta": texto, "resposta": resposta_texto})
    historico = historico[-50:]
    salvar_historico_json(historico)

    if entrada.usuario_id:
        try:
            db.add(
                HistoricoMark(
                    usuario_id=entrada.usuario_id,
                    remetente="usuário",
                    mensagem=texto,
                )
            )
            db.add(
                HistoricoMark(
                    usuario_id=entrada.usuario_id,
                    remetente="MARK",
                    mensagem=resposta_texto,
                )
            )
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            print("[ERRO SALVAR DB responder_mark]:", e)

    return {"resposta": resposta_texto}


# =====================================================================
# 🔥 ENDPOINT /stream — salva JSON (DB via /registrar_historico)
# =====================================================================
@router.post("/stream")
async def stream_mark(entrada: EntradaMARK, db: Session = Depends(get_db)):

    texto = (entrada.mensagem or "").strip()
    if not texto:

        async def vazio():
            yield "Envie uma mensagem válida."

        return StreamingResponse(vazio(), media_type="text/plain")

    mensagens = montar_mensagens_base(texto, entrada.usuario_id, db)
    modelo_usado = entrada.modelo or MARK_MODEL_DEFAULT

    async def token_generator():

        full = ""

        try:
            stream = await client.chat.completions.create(
                model=modelo_usado,
                messages=mensagens,
                temperature=0.4,
                stream=True,
                timeout=60,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full += delta
                    yield delta

        except Exception as e:
            erro = f"[ERRO IA] Error code: 401 - {e}"
            yield erro

        # Atualiza JSON de contexto (independente de salvar em banco)
        historico = carregar_historico_json()
        historico.append({"pergunta": texto, "resposta": full})
        historico = historico[-50:]
        salvar_historico_json(historico)

    return StreamingResponse(token_generator(), media_type="text/plain")


# =====================================================================
# 🔥 ENDPOINT /registrar_historico — chamado pelo HTML após stream
# =====================================================================
@router.post("/registrar_historico")
async def registrar_historico(payload: RegistrarHistoricoPayload, db: Session = Depends(get_db)):
    """
    Salva no banco a pergunta e a resposta do MARK.
    Chamado pelo HTML após terminar o streaming.
    """
    if not payload.usuario_id:
        return {"ok": False, "motivo": "usuario_id ausente"}

    try:
        db.add(
            HistoricoMark(
                usuario_id=payload.usuario_id,
                remetente="usuário",
                mensagem=payload.mensagem,
            )
        )
        db.add(
            HistoricoMark(
                usuario_id=payload.usuario_id,
                remetente="MARK",
                mensagem=payload.resposta,
            )
        )
        db.commit()
        return {"ok": True}
    except SQLAlchemyError as e:
        db.rollback()
        print("[ERRO registrar_historico]", e)
        raise HTTPException(status_code=500, detail="Erro ao salvar histórico no banco.")


# =====================================================================
# 🔍 ENDPOINT: /mark/historico_v2  (lista o histórico do banco)
# =====================================================================
@router.get("/historico_v2")
async def listar_historico_mark(
    busca: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Lista o histórico de conversas salvas na tabela historico_mark.
    """

    try:
        query = db.query(HistoricoMark)

        if busca:
            like = f"%{busca}%"
            query = query.filter(HistoricoMark.mensagem.ilike(like))

        registros = query.order_by(HistoricoMark.data_envio.desc()).limit(300).all()

        retorno = []
        for h in registros:
            data = h.data_envio
            if isinstance(data, datetime):
                data_str = data.isoformat()
            elif data is None:
                data_str = None
            else:
                try:
                    data_str = str(data)
                except Exception:
                    data_str = None

            retorno.append(
                {
                    "id": h.id,
                    "usuario_id": h.usuario_id,
                    "remetente": h.remetente,
                    "mensagem": h.mensagem or "",
                    "data_envio": data_str,
                }
            )

        return retorno

    except SQLAlchemyError as e:
        print("[ERRO historico_v2 SQLAlchemy]", e)
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco de dados do histórico.")
    except Exception as e:
        print("[ERRO historico_v2]", e)
        raise HTTPException(status_code=500, detail=f"Erro inesperado ao carregar histórico: {e}")


# =====================================================================
# /responder_simples – teste rápido de IA (sem empresa)
# =====================================================================
@router.post("/responder_simples")
async def responder_simples(entrada: EntradaSimples):
    texto = entrada.mensagem.strip()
    if not texto:
        return {"resposta": "Envie uma mensagem para teste."}

    mensagens = [
        {"role": "system", "content": "Você é o MARK."},
        {"role": "user", "content": texto},
    ]
    return {"resposta": await chamar_openai(mensagens)}
