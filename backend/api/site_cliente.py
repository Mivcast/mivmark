# backend/api/site_cliente.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import SessionLocal
from backend.models import Empresa
from jinja2 import Template
from pathlib import Path
import os

router = APIRouter()

# 🗂 Diretórios a partir da raiz do projeto (C:\Projetos\mivmark)
RAIZ_PROJETO = Path(__file__).resolve().parents[2]  # .../backend/api -> .../backend -> .../mivmark

CAMINHO_MODELO = RAIZ_PROJETO / "templates_html" / "modelo_site_cliente.html"
PASTA_SAIDA = RAIZ_PROJETO / "data" / "sites_gerados"


class DadosSiteCliente(BaseModel):
    usuario_id: int
    bio: str | None = None
    agendamento_ativo: bool = False
    horarios_disponiveis: list[str] = []
    informacoes_adicionais: str | None = None


def _slug_nome(nome: str) -> str:
    """
    Gera um slug simples: tudo minúsculo, espaços viram underscore.
    Ex.: 'Restaurante do Judas' -> 'restaurante_do_judas'
    """
    nome = (nome or "").strip().lower().replace(" ", "_")
    # Evita caracteres estranhos em nome de arquivo
    permitidos = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    return "".join(ch for ch in nome if ch in permitidos) or "site"


def gerar_site_cliente(dados: DadosSiteCliente):
    """
    Gera o site HTML do cliente com base no modelo Jinja e nos dados da empresa.
    O HTML fica em: data/sites_gerados/NOME_EMPRESA.html
    """
    db = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == dados.usuario_id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada para este usuário.")

        if not CAMINHO_MODELO.exists():
            raise HTTPException(status_code=500, detail="Modelo de site não encontrado.")

        with CAMINHO_MODELO.open("r", encoding="utf-8") as f:
            template = Template(f.read())

        slug_empresa = _slug_nome(getattr(empresa, "nome_empresa", "site"))

        # Renderiza o HTML com TODOS os dados que o modelo usa
        site_renderizado = template.render(
            # Dados da empresa
            nome_empresa=getattr(empresa, "nome_empresa", "") or "",
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

            # Dados extras específicos do módulo Página e Chat do Cliente
            bio=dados.bio or "",
            informacoes_adicionais=dados.informacoes_adicionais or "",
            agendamento_ativo=dados.agendamento_ativo,
            horarios_disponiveis=dados.horarios_disponiveis or [],

            # Usado pelo chat público para identificar a empresa
            empresa_slug=slug_empresa,
        )

        # Garante que a pasta de saída exista
        PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

        nome_arquivo = f"{slug_empresa}.html"
        caminho_saida = PASTA_SAIDA / nome_arquivo

        with caminho_saida.open("w", encoding="utf-8") as f_out:
            f_out.write(site_renderizado)

        # Se você configurar SITES_BASE_URL no Render, montamos a URL pública
        # Ex.: SITES_BASE_URL=https://mivmark-backend.onrender.com/sites
        base_url = os.getenv("SITES_BASE_URL")
        url_publica = f"{base_url.rstrip('/')}/{nome_arquivo}" if base_url else None

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
