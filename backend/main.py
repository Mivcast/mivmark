from fastapi import FastAPI
from backend import models
from backend.database import engine
from backend.api import mark_ia
from backend.api import agenda  # linha nova
from backend.api import site_cliente
from backend.api import usuario
from backend.api import chat_publico
from backend.api.aplicativo import router as aplicativo_router  # <- ESSA LINHA AQUI
from backend.database import Base, engine
from backend.models import planos  # importa os modelos que você criou
from backend.api.planos import router as planos_router


Base.metadata.create_all(bind=engine)





# Carrega variáveis do .env
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

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
    marketing
)
from backend.api import mercado_pago_pagamento

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou use o domínio real do seu frontend/site no lugar do "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rotas da API
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
app.include_router(agenda.router)  # linha nova
app.include_router(site_cliente.router)
app.include_router(usuario.router)
app.include_router(chat_publico.router)
app.include_router(aplicativo_router)
app.include_router(planos_router)



# Cria as tabelas automaticamente
models.Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"mensagem": "MARK backend rodando!"}
