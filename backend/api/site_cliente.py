from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import SessionLocal
from models import Empresa
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
    informacoes_adicionais: str = ""

@router.post("/site-cliente/gerar")
def gerar_site_cliente(dados: DadosSiteCliente):
    db = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == dados.usuario_id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada.")

        if not os.path.exists(CAMINHO_MODELO):
            raise HTTPException(status_code=500, detail="Modelo HTML não encontrado.")

        # Carrega o HTML modelo
        with open(CAMINHO_MODELO, "r", encoding="utf-8") as f:
            template = Template(f.read())

        redes = empresa.redes_sociais or {}
        produtos = empresa.produtos or []

        site_renderizado = template.render(
            nome_empresa=empresa.nome_empresa,
            descricao=empresa.descricao,
            nicho=empresa.nicho,
            logo_url=empresa.logo_url,
            whatsapp=redes.get("whatsapp", ""),
            instagram=redes.get("instagram", ""),
            facebook=redes.get("facebook", ""),
            tiktok=redes.get("tiktok", ""),
            youtube=redes.get("youtube", ""),
            produtos=produtos,
            info=dados.informacoes_adicionais,
            rua=empresa.rua or "",
            numero=empresa.numero or "",
            bairro=empresa.bairro or "",
            cidade=empresa.cidade or "",
            cep=empresa.cep or "",
            cnpj=empresa.cnpj or ""
        )

        # Gera HTML direto na pasta principal com nome_empresa.html
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        nome_arquivo = f"{empresa.nome_empresa.replace(' ', '_')}.html"
        caminho_saida = os.path.join(PASTA_SAIDA, nome_arquivo)

        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(site_renderizado)

        return {"mensagem": "Site gerado com sucesso!", "caminho": caminho_saida}
    finally:
        db.close()
