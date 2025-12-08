# backend/api/site_cliente.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import SessionLocal
from backend.models import Empresa
from jinja2 import Template
from pathlib import Path
import os
import shutil

router = APIRouter()

# Diretórios base independentes da pasta onde o servidor é iniciado
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CAMINHO_MODELO = BASE_DIR / "templates_html" / "modelo_site_cliente.html"
PASTA_SAIDA = BASE_DIR / "data" / "sites_gerados"


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
        empresa = (
            db.query(Empresa)
            .filter(Empresa.usuario_id == dados.usuario_id)
            .first()
        )
        if not empresa:
            raise HTTPException(
                status_code=404,
                detail="Empresa não encontrada para este usuário.",
            )

        if not CAMINHO_MODELO.exists():
            raise HTTPException(
                status_code=500,
                detail="Modelo de site não encontrado.",
            )

        template = Template(CAMINHO_MODELO.read_text(encoding="utf-8"))

        # Slug da empresa (usado no nome do arquivo e no chat)
        slug_empresa = (empresa.nome_empresa or "site").replace(" ", "_")

        site_renderizado = template.render(
            nome_empresa=empresa.nome_empresa or "",
            nicho=getattr(empresa, "nicho", "") or "",
            descricao=getattr(empresa, "descricao", "") or "",
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
            empresa_slug=slug_empresa,  # usado no iframe do chat
        )

        # Garante que a pasta de saída existe
        PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

        # 🔹 Copia/atualiza a pasta assets (CSS, JS, imagens) para data/sites_gerados/assets
        origem_assets = BASE_DIR / "templates_html" / "assets"
        destino_assets = PASTA_SAIDA / "assets"
        if origem_assets.is_dir():
            shutil.copytree(origem_assets, destino_assets, dirs_exist_ok=True)

        nome_arquivo = f"{slug_empresa}.html"
        caminho_saida = PASTA_SAIDA / nome_arquivo
        caminho_saida.write_text(site_renderizado, encoding="utf-8")

        # URL pública do site (Render)
        # Ex.: SITES_BASE_URL=https://mivmark-backend.onrender.com/sites
        base_url = os.getenv("SITES_BASE_URL")
        url_publica = (
            f"{base_url.rstrip('/')}/{nome_arquivo}"
            if base_url
            else None
        )

        return {
            "mensagem": "Site gerado com sucesso!",
            "caminho": str(caminho_saida),
            "arquivo": nome_arquivo,
            "url_publica": url_publica,
        }
    finally:
        db.close()


@router.post("/site_cliente/gerar")
def api_gerar_site_cliente(dados: DadosSiteCliente):
    return gerar_site_cliente(dados)
