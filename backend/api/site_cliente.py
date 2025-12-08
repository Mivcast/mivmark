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

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
RAIZ_PROJETO = BASE_DIR.parent                    # C:\Projetos\mivmark

CAMINHO_MODELO = RAIZ_PROJETO / "templates_html" / "modelo_site_cliente.html"
PASTA_SAIDA = RAIZ_PROJETO / "data" / "sites_gerados"
ASSETS_ORIGEM = RAIZ_PROJETO / "templates_html" / "assets"
ASSETS_DESTINO = PASTA_SAIDA / "assets"


class DadosSiteCliente(BaseModel):
    usuario_id: int
    bio: str
    agendamento_ativo: bool = False
    horarios_disponiveis: list[str] = []
    informacoes_adicionais: str | None = None


def garantir_assets():
    """
    Garante que a pasta data/sites_gerados/assets exista no servidor
    copiando a partir de templates_html/assets.
    Isso resolve o CSS/imagens quebrados no Render.
    """
    if not ASSETS_ORIGEM.exists():
        return

    ASSETS_DESTINO.parent.mkdir(parents=True, exist_ok=True)

    # copia tudo, sobrescrevendo se já existir
    shutil.copytree(
        ASSETS_ORIGEM,
        ASSETS_DESTINO,
        dirs_exist_ok=True
    )


def gerar_site_cliente(dados: DadosSiteCliente):
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
                detail="Empresa não encontrada para este usuário."
            )

        if not CAMINHO_MODELO.exists():
            raise HTTPException(
                status_code=500,
                detail="Modelo de site não encontrado."
            )

        # garante CSS/imagens
        garantir_assets()

        with CAMINHO_MODELO.open("r", encoding="utf-8") as f:
            template = Template(f.read())

        slug_empresa = (empresa.nome_empresa or "site").strip().replace(" ", "_")

        # URL que o iframe do chat vai abrir
        chat_url = f"/chat_publico?empresa={slug_empresa}"

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
            empresa_slug=slug_empresa,
            chat_url=chat_url,
        )

        PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"{slug_empresa}.html"
        caminho_saida = PASTA_SAIDA / nome_arquivo

        with caminho_saida.open("w", encoding="utf-8") as f_out:
            f_out.write(site_renderizado)

        base_url = os.getenv("SITES_BASE_URL")  # ex: https://mivmark-backend.onrender.com/sites
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
