# backend/api/chat_publico.py

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from backend.database import SessionLocal
from backend.models import Empresa
from openai import OpenAI
import os

router = APIRouter()

# 🔑 Cliente OpenAI (SDK novo)
def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# 🔹 Widget do chat público (carregado via iframe no site do cliente)
@router.get("/chat_publico", response_class=HTMLResponse)
def chat_publico(empresa: str):
    """
    `empresa` vem em formato slug: Restaurante_do_judas, Sorveteria_do_Ze etc.
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="utf-8" />
        <title>Atendente Virtual</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
            }}
            #chatbox {{
                position: fixed;
                bottom: 0;
                right: 0;
                width: 320px;
                max-width: 100vw;
                height: 420px;
                display: flex;
                flex-direction: column;
                border-radius: 12px 12px 0 0;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.15);
                background: #ffffff;
                overflow: hidden;
            }}
            #header {{
                background: #0067ff;
                color: #fff;
                padding: 10px 12px;
                font-weight: bold;
                font-size: 14px;
            }}
            #mensagens {{
                flex: 1;
                overflow-y: auto;
                padding: 10px;
                background: #f7f7f7;
                font-size: 13px;
            }}
            #inputArea {{
                display: flex;
                border-top: 1px solid #ddd;
            }}
            #inputArea input {{
                flex: 1;
                padding: 8px 10px;
                border: none;
                outline: none;
                font-size: 13px;
            }}
            #inputArea button {{
                padding: 0 16px;
                border: none;
                background: #0067ff;
                color: #fff;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div id="chatbox">
            <div id="header">🤖 Atendente Virtual</div>
            <div id="mensagens"></div>
            <div id="inputArea">
                <input type="text" id="pergunta" placeholder="Digite sua pergunta..." />
                <button onclick="enviar()">Enviar</button>
            </div>
        </div>

        <script>
            const EMPRESA = "{empresa}";

            async function enviar() {{
                const input = document.getElementById('pergunta');
                const mensagens = document.getElementById('mensagens');
                const pergunta = input.value.trim();
                if (!pergunta) return;

                mensagens.innerHTML += "<p><strong>Você:</strong> " + pergunta + "</p>";
                input.value = "";

                try {{
                    const resp = await fetch(
                        "/chat_publico/perguntar?pergunta=" + encodeURIComponent(pergunta) +
                        "&empresa=" + encodeURIComponent(EMPRESA)
                    );
                    const dados = await resp.json();
                    mensagens.innerHTML += "<p><strong>Atendente:</strong> " + dados.resposta + "</p>";
                }} catch (e) {{
                    mensagens.innerHTML += "<p><strong>Atendente:</strong> Erro ao conectar ao servidor.</p>";
                }}

                mensagens.scrollTop = mensagens.scrollHeight;
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# 🔹 Endpoint chamado pelo JS acima
@router.get("/chat_publico/perguntar")
def responder_chat_publico(pergunta: str, empresa: str):
    """
    Responde o cliente final usando dados reais da empresa + IA.
    `empresa` vem como slug: Restaurante_do_judas -> "Restaurante do judas"
    """
    db = SessionLocal()
    try:
        nome_empresa = empresa.replace("_", " ")

        empresa_dados = (
            db.query(Empresa)
            .filter(Empresa.nome_empresa == nome_empresa)
            .first()
        )

        if not empresa_dados:
            return JSONResponse(
                content={"resposta": "Empresa não encontrada. Peça para o responsável configurar os dados no painel MivMark."}
            )

        client = get_client()
        if client is None:
            return JSONResponse(
                content={"resposta": "Atendente temporariamente indisponível. Falta configurar a chave da IA no sistema."}
            )

        # 🔹 Monta contexto com os campos que sabemos que existem no modelo Empresa
        contexto = f"""
Você é um atendente virtual simpático, educado e objetivo de uma empresa chamada "{empresa_dados.nome_empresa}".

Dados da empresa:
- Nicho / segmento: {getattr(empresa_dados, "nicho", "")}
- Descrição: {getattr(empresa_dados, "descricao", "")}
- Cidade: {getattr(empresa_dados, "cidade", "")}
- Endereço: {getattr(empresa_dados, "rua", "")}, {getattr(empresa_dados, "numero", "")}, {getattr(empresa_dados, "bairro", "")}
- CEP: {getattr(empresa_dados, "cep", "")}
- WhatsApp: {getattr(empresa_dados, "whatsapp", "")}
- Instagram: {getattr(empresa_dados, "instagram", "")}
- Facebook: {getattr(empresa_dados, "facebook", "")}
- TikTok: {getattr(empresa_dados, "tiktok", "")}
- YouTube: {getattr(empresa_dados, "youtube", "")}

Regras:
- Responda SEMPRE em português do Brasil.
- Fale de forma clara, curta e amigável.
- Responda apenas sobre serviços, produtos, preços aproximados, horários, endereço, contato e informações comerciais relacionadas à empresa.
- Se o cliente perguntar algo que foge da empresa, diga educadamente que não tem essa informação.
"""

        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user", "content": pergunta},
            ],
        )

        texto_resposta = resposta.choices[0].message.content.strip()
        return JSONResponse(content={"resposta": texto_resposta})

    except Exception as e:
        # Nunca deixar estourar erro 500 no iframe — sempre responder algo
        return JSONResponse(
            content={"resposta": f"Erro ao responder: {str(e)}"}
        )
    finally:
        db.close()
