from fastapi import FastAPI
from models import planos  # modelos diretos
from database import Base, engine
from api import (
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
    mercado_pago_pagamento
)
from api.aplicativo import router as aplicativo_router
from api.planos import router as planos_router

# Cria as tabelas automaticamente
Base.metadata.create_all(bind=engine)

# Carrega variáveis do .env
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Inicializa FastAPI
app = FastAPI()

# Configura CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(agenda.router)
app.include_router(site_cliente.router)
app.include_router(usuario.router)
app.include_router(chat_publico.router)
app.include_router(aplicativo_router)
app.include_router(planos_router)

@app.get("/")
def home():
    return {"mensagem": "MARK backend rodando!"}
