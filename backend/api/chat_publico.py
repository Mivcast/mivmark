from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from backend.models import Usuario, Empresa
from backend.database import SessionLocal
from backend.api.auth import get_current_user
from pydantic import BaseModel
import openai
import os

router = APIRouter()

# Use a chave da sua conta OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# HTML do chat (visível na versão web)
@router.get("/chat_publico", response_class=HTMLResponse)
def chat_publico():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Atendente Virtual</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; }
            #chatbox { position: fixed; bottom: 0; right: 20px; width: 350px; background: white; border: 1px solid #ccc; border-radius: 10px 10px 0 0; display: flex; flex-direction: column; height: 400px; }
            #mensagens { flex: 1; overflow-y: auto; padding: 10px; }
            #inputArea { display: flex; }
            input { flex: 1; padding: 10px; border: none; border-top: 1px solid #ccc; }
            button { padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <div id="chatbox">
            <div id="mensagens"></div>
            <div id="inputArea">
                <input type="text" id="pergunta" placeholder="Digite sua pergunta..." />
                <button onclick="enviar()">Enviar</button>
            </div>
        </div>

        <script>
            async function enviar() {
                const input = document.getElementById('pergunta');
                const mensagens = document.getElementById('mensagens');
                const pergunta = input.value;
                if (!pergunta) return;

                mensagens.innerHTML += `<p><strong>Você:</strong> ${pergunta}</p>`;
                input.value = "";

                const resposta = await fetch(`/chat_publico/perguntar?pergunta=${encodeURIComponent(pergunta)}&empresa=MivCast_Marketing_Digital`);
                const dados = await resposta.json();

                mensagens.innerHTML += `<p><strong>Atendente:</strong> ${dados.resposta}</p>`;
                mensagens.scrollTop = mensagens.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# Schema da pergunta recebida
class Pergunta(BaseModel):
    pergunta: str
    empresa: str

# Endpoint que responde baseado nos dados da empresa
@router.get("/chat_publico/perguntar")
def responder_chat_publico(pergunta: str, empresa: str):
    db = SessionLocal()
    try:
        empresa_dados = db.query(Empresa).filter(Empresa.nome_empresa == empresa.replace("_", " ")).first()
        if not empresa_dados:
            return JSONResponse(content={"resposta": "Empresa não encontrada."})

        # Monta o contexto com os dados reais
        contexto = f"""
Você é um atendente virtual simpático e objetivo. Responda com base nas informações da empresa abaixo:

Nome: {empresa_dados.nome_empresa}
Descrição: {empresa_dados.descricao}
Nicho: {empresa_dados.nicho}
CNPJ: {empresa_dados.cnpj}
Endereço: {empresa_dados.rua}, {empresa_dados.numero}, {empresa_dados.bairro} - {empresa_dados.cidade}/{empresa_dados.cep}
Redes Sociais: {empresa_dados.redes_sociais}
Informações adicionais: {empresa_dados.informacoes_adicionais}
Produtos: {[p['nome'] + ' - R$' + str(p['preco']) for p in empresa_dados.produtos]}

Pergunta do cliente: {pergunta}
"""

        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user", "content": pergunta}
            ]
        )

        texto_resposta = resposta.choices[0].message.content.strip()
        return JSONResponse(content={"resposta": texto_resposta})

    except Exception as e:
        return JSONResponse(content={"resposta": f"Erro ao responder: {str(e)}"})

    finally:
        db.close()
