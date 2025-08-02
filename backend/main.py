from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

from backend.database import Base, engine
from backend import models
from backend.models import planos

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
    mercado_pago_pagamento,
    agenda,
    site_cliente,
    usuario,
    chat_publico
)
from backend.api.aplicativo import router as aplicativo_router
from backend.api.planos import router as planos_router

# Carrega variáveis de ambiente
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Cria a aplicação
app = FastAPI()

# Criação automática das tabelas no startup
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Substituir pelo domínio real em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
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

@app.get("/")
def home():
    return {"mensagem": "MARK backend rodando!"}
