# backend/main.py
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.database import Base, engine
from backend import models  # garante que os models sejam registrados
from backend.api import email_teste
from backend.api.ideias import router as ideias_router
from backend.api import consultor_mensal
from backend.api.consultor_mensal import router as consultor_mensal_router



# ============================================
# 🔹 Caminho raiz do projeto e .env
# ============================================
# RAIZ_PROJETO = pasta "mivmark"
RAIZ_PROJETO = Path(__file__).resolve().parents[1]

# Carrega .env localmente (no Render usamos Environment Vars)
env_path = RAIZ_PROJETO / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Pasta dos sites gerados: mivmark/data/sites_gerados
DIR_SITES = RAIZ_PROJETO / "data" / "sites_gerados"
DIR_SITES.mkdir(parents=True, exist_ok=True)


# ============================================
# 🔹 Cria o app FastAPI
# ============================================
app = FastAPI(title="MivMark API")


# ============================================
# 🔹 CORS
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois você pode trocar pelo domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 🔹 Servir arquivos estáticos dos sites gerados
# ============================================
# Exemplo:
#   https://mivmark-backend.onrender.com/sites/Restaurante_do_joao.html
# e assets:
#   https://mivmark-backend.onrender.com/sites/assets/css/style.css
app.mount("/sites", StaticFiles(directory=str(DIR_SITES), html=True), name="sites")


# ============================================
# 🔹 Cliente OPENAI (usado em mark_ia / chat_publico)
# ============================================
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return AsyncOpenAI(api_key=api_key)


# ============================================
# 🔹 Criar tabelas
# ============================================
Base.metadata.create_all(bind=engine)


# ============================================
# 🔹 Imports e Rotas
# ============================================
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
app.include_router(email_teste.router)
app.include_router(ideias_router)
app.include_router(consultor_mensal_router)




@app.get("/")
def home():
    return {"mensagem": "MARK backend rodando!"}
