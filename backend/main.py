# backend/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend import models
from backend.database import Base, engine

# 🔹 Carrega variáveis do .env (pasta raiz do projeto)
BASE_DIR = Path(__file__).resolve().parent
SITES_DIR = BASE_DIR.parent / "data" / "sites_gerados"

app.mount("/sites", StaticFiles(directory=SITES_DIR, html=True), name="sites")


# 🔹 Função utilitária para obter cliente OpenAI (usada em mark_ia.py)
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    print("DEBUG OPENAI KEY LEN:", len(api_key) if api_key else "NENHUMA")
    print("DEBUG OPENAI KEY INICIO:", api_key[:10] if api_key else "NENHUMA")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)


# 🔹 Imports dos routers da API
from backend.api import (  # noqa: E402
    auth,
    empresa,
    consultoria,
    orcamentos,
    pagamentos,
    historico,
    arquivos,
    historico_mark,
    mark_ia,
    cursos,
    marketing,
    agenda,
    site_cliente,
    usuario,
    chat_publico,
    mercado_pago_pagamento,
)
from backend.api.aplicativo import router as aplicativo_router  # noqa: E402
from backend.api.planos import router as planos_router  # noqa: E402
from backend.api.cupons import router as cupons_router  # noqa: E402


# 🔹 Cria as tabelas automaticamente (uma vez só)
Base.metadata.create_all(bind=engine)


app = FastAPI(title="MivMark API")


# 🔹 Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois você pode trocar pelo domínio real do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🔹 Monta pasta estática para os sites gerados
DIR_SITES = BASE_DIR / "data" / "sites_gerados"
DIR_SITES.mkdir(parents=True, exist_ok=True)

# Assim, qualquer arquivo em data/sites_gerados/xxx.html fica acessível em /sites/xxx.html
app.mount("/sites", StaticFiles(directory=str(DIR_SITES)), name="sites")


# 🔹 Rotas da API
app.include_router(auth.router)
app.include_router(empresa.router)
app.include_router(consultoria.router)
app.include_router(orcamentos.router)
app.include_router(pagamentos.router)
app.include_router(historico.router)
app.include_router(arquivos.router)
app.include_router(historico_mark.router)
app.include_router(mark_ia.router, prefix="/mark")
app.include_router(cursos.router)
app.include_router(mercado_pago_pagamento.router, prefix="/api")
app.include_router(marketing.router)
app.include_router(agenda.router)
app.include_router(site_cliente.router)
app.include_router(usuario.router)
app.include_router(chat_publico.router)
app.include_router(aplicativo_router)
app.include_router(planos_router)
app.include_router(cupons_router)


@app.get("/")
def home():
    return {"mensagem": "MARK backend rodando!"}
