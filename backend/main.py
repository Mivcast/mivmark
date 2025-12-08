# backend/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.database import Base, engine
from backend import models

# ============================================
# 🔹 Caminho raiz e .env
# ============================================
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

load_dotenv(dotenv_path=RAIZ_PROJETO / ".env")

DIR_SITES = RAIZ_PROJETO / "data" / "sites_gerados"
DIR_SITES.mkdir(parents=True, exist_ok=True)

# ============================================
# 🔹 Cria o app FastAPI (PRECISA vir antes do mount)
# ============================================
app = FastAPI(title="MivMark API")

# ============================================
# 🔹 Configuração de CORS
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# 🔹 Monta os sites (AGORA pode usar o app)
# ============================================
app.mount("/sites", StaticFiles(directory=str(DIR_SITES), html=True), name="sites")

# ============================================
# 🔹 OpenAI client
# ============================================
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)

# ============================================
# 🔹 Cria tabelas
# ============================================
Base.metadata.create_all(bind=engine)

# ============================================
# 🔹 Importa as rotas
# ============================================
from backend.api import (
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
from backend.api.aplicativo import router as aplicativo_router
from backend.api.planos import router as planos_router
from backend.api.cupons import router as cupons_router

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
