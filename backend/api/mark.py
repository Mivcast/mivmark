from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from typing import Optional, Dict, Any, List
import os
import json

from openai import AsyncOpenAI

from backend.database import get_db
from backend.models import Empresa

router = APIRouter(prefix="/mark", tags=["mark"])


class MarkStreamRequest(BaseModel):
    mensagem: str
    usuario_id: Optional[int] = None


def empresa_to_dict(empresa: Empresa) -> Dict[str, Any]:
    """
    Converte o modelo Empresa para um dicionário simples.
    """
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


def obter_empresa_do_usuario(
    db: Session, usuario_id: Optional[int]
) -> Optional[Dict[str, Any]]:
    """
    Busca a empresa vinculada ao usuário.
    Se usuario_id for None, retorna a empresa mais recentemente atualizada (fallback).
    """
    query = db.query(Empresa)

    if usuario_id is not None:
        query = query.filter(Empresa.usuario_id == usuario_id)

    empresa = query.order_by(Empresa.atualizado_em.desc()).first()
    if not empresa:
        return None

    return empresa_to_dict(empresa)


def montar_mensagens_mark(
    texto_usuario: str, empresa: Optional[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Monta o array de mensagens para enviar ao modelo da OpenAI,
    incluindo o contexto da empresa (quando existir).
    """
    if empresa:
        empresa_json = json.dumps(empresa, ensure_ascii=False, indent=2)
        system_content = (
            "Você é o MARK, consultor de Branding e Marketing do sistema MivMark, "
            "criado pelo Matheus Nascimento (MivCast). "
            "Responda SEMPRE em português do Brasil, com exemplos práticos e aplicáveis "
            "para pequenos e médios negócios.\n\n"
            "Você tem acesso aos dados reais da empresa do usuário, em formato JSON abaixo. "
            "Use SEMPRE essas informações como base das suas respostas, evitando inventar dados.\n\n"
            "Se o usuário perguntar algo como 'qual é minha empresa?' ou 'qual é o meu nicho?', "
            "responda usando diretamente os campos do JSON.\n\n"
            "DADOS DA EMPRESA (JSON):\n"
            f"{empresa_json}"
        )
    else:
        system_content = (
            "Você é o MARK, consultor de Branding e Marketing do sistema MivMark, "
            "criado pelo Matheus Nascimento (MivCast). "
            "Responda SEMPRE em português do Brasil, com exemplos práticos.\n\n"
            "Neste momento você NÃO recebeu dados da empresa do usuário a partir do sistema. "
            "Quando for relevante, explique isso de forma educada e oriente o usuário a preencher "
            "o módulo 'Empresa' dentro do sistema MivMark para que você consiga personalizar melhor "
            "as respostas. Enquanto isso, responda de forma mais genérica, deixando claro que não "
            "está vendo os dados da empresa dele agora."
        )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": texto_usuario},
    ]
    return messages


@router.post("/stream")
async def mark_stream(req: MarkStreamRequest, db: Session = Depends(get_db)):
    """
    Endpoint de streaming usado pelo chat HTML (mark_chat.html).

    - Recebe a mensagem do usuário e o usuario_id (quando logado).
    - Busca a empresa correspondente no banco.
    - Monta o contexto e chama a OpenAI em streaming.
    """
    texto = (req.mensagem or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")

    # DEBUG no terminal
    print(f"[MARK] mensagem='{texto}' | usuario_id={req.usuario_id}")

    # 1) Buscar empresa do usuário (se houver)
    empresa_dict = obter_empresa_do_usuario(db, req.usuario_id)

    print(
        f"[MARK] empresa_encontrada = "
        f"{'SIM' if empresa_dict else 'NAO'} para usuario_id={req.usuario_id}"
    )

    # 2) Montar mensagens para o modelo
    messages = montar_mensagens_mark(texto, empresa_dict)

    # 3) Cliente OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500, detail="OPENAI_API_KEY não configurada no servidor."
        )

    client = AsyncOpenAI(api_key=api_key)
    model_name = os.getenv("MARK_MODEL", "gpt-5.1-mini")

    async def stream_generator():
        try:
            stream = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # Compatível com diferentes versões do SDK
                content = getattr(delta, "content", None)
                if content is None and isinstance(delta, dict):
                    content = delta.get("content")
                if content:
                    yield content
        except Exception as e:
            msg_erro = (
                "Desculpe, tive um problema ao gerar a resposta agora. "
                "Avise o Matheus para verificar a configuração da chave da OpenAI "
                "ou a conexão do servidor. "
                f"(detalhe técnico: {e})"
            )
            yield msg_erro

    return StreamingResponse(stream_generator(), media_type="text/plain")
