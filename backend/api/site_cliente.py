# backend/api/site_cliente.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import SessionLocal
from backend.models import Empresa
from jinja2 import Template
import os

router = APIRouter()

CAMINHO_MODELO = "templates_html/modelo_site_cliente.html"
PASTA_SAIDA = "data/sites_gerados"

class DadosSiteCliente(BaseModel):
    usuario_id: int
    bio: str
    agendamento_ativo: bool = False
    horarios_disponiveis: list[str] = []
    informacoes_adicionais: str | None = None


def gerar_site_cliente(dados: DadosSiteCliente):
    """
    Gera o site HTML do cliente com base no modelo Jinja e nos dados da empresa.
    """
    db = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == dados.usuario_id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada para este usuário.")

        # Carrega o modelo HTML
        if not os.path.exists(CAMINHO_MODELO):
            raise HTTPException(status_code=500, detail="Modelo de site não encontrado.")

        with open(CAMINHO_MODELO, "r", encoding="utf-8") as f:
            template = Template(f.read())

        # Renderiza o HTML com os dados da empresa
        site_renderizado = template.render(
            nome_empresa=empresa.nome_empresa or "",
            nicho=empresa.nicho or "",
            descricao=empresa.descricao or "",
            logo_url=getattr(empresa, "logo_url", "") or "",
            whatsapp=getattr(empresa, "whatsapp", "") or "",
            instagram=getattr(empresa, "instagram", "") or "",
            facebook=getattr(empresa, "facebook", "") or "",
            tiktok=getattr(empresa, "tiktok", "") or "",
            youtube=getattr(empresa, "youtube", "") or "",
            rua=getattr(empresa, "rua", "") or "",
            numero=getattr(empresa, "numero", "") or "",
            bairro=getattr(empresa, "bairro", "") or "",
            cidade=getattr(empresa, "cidade", "") or "",
            cep=getattr(empresa, "cep", "") or "",
            cnpj=getattr(empresa, "cnpj", "") or "",
            bio=dados.bio or "",
            informacoes_adicionais=dados.informacoes_adicionais or "",
            agendamento_ativo=dados.agendamento_ativo,
            horarios_disponiveis=dados.horarios_disponiveis or [],
        )







        # Gera HTML direto na pasta /data/sites_gerados com Nome_da_Empresa.html
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        slug = (empresa.nome_empresa or "site").replace(" ", "_")
        nome_arquivo = f"{slug}.html"
        caminho_saida = os.path.join(PASTA_SAIDA, nome_arquivo)

        with open(caminho_saida, "w", encoding="utf-8") as f_out:
            f_out.write(site_renderizado)

        # Monta URL pública com base em uma env var
        # Exemplo de valor em produção: SITES_BASE_URL=https://mivmark-backend.onrender.com/sites
        base_url = os.getenv("SITES_BASE_URL")
        url_publica = (
            f"{base_url.rstrip('/')}/{nome_arquivo}"
            if base_url
            else None
        )

        return {
            "mensagem": "Site gerado com sucesso!",
            "caminho": caminho_saida,
            "arquivo": nome_arquivo,
            "url_publica": url_publica,
        }
    finally:
        db.close()


# 🔹 Rota pública para o frontend chamar
@router.post("/site_cliente/gerar")
def api_gerar_site_cliente(dados: DadosSiteCliente):
    return gerar_site_cliente(dados)
