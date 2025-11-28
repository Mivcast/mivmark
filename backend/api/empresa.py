from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Empresa, Usuario
from backend.api.auth import get_current_user
from datetime import datetime
from backend.models import CardMarketing

# ✅ Import para geração do site do cliente
from backend.api.site_cliente import gerar_site_cliente, DadosSiteCliente

router = APIRouter()

# -------- SCHEMAS --------
class FuncionarioSchema(BaseModel):
    nome: str
    data_nascimento: Optional[str] = None
    funcao: str
    telefone: Optional[str] = None
    observacao: Optional[str] = None

class ProdutoSchema(BaseModel):
    nome: str
    preco: float
    descricao: str
    imagem: Optional[str] = None

class EmpresaSchema(BaseModel):
    nome_empresa: str
    descricao: str
    nicho: str
    logo_url: Optional[str] = None
    funcionarios: List[FuncionarioSchema] = []
    produtos: List[ProdutoSchema] = []
    redes_sociais: dict = {}
    informacoes_adicionais: str = ""
    cnpj: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None

# -------- FUNÇÃO AUXILIAR --------
def empresa_to_dict(empresa: Empresa) -> dict:
    return {
        "nome_empresa": empresa.nome_empresa,
        "descricao": empresa.descricao,
        "nicho": empresa.nicho,
        "logo_url": empresa.logo_url,
        "funcionarios": empresa.funcionarios,
        "produtos": empresa.produtos,
        "redes_sociais": empresa.redes_sociais,
        "informacoes_adicionais": empresa.informacoes_adicionais,
        "cnpj": empresa.cnpj,
        "rua": empresa.rua,
        "numero": empresa.numero,
        "bairro": empresa.bairro,
        "cidade": empresa.cidade,
        "cep": empresa.cep,
        "atualizado_em": empresa.atualizado_em,
    }

# -------- ROTAS PRINCIPAIS (COM AUTENTICAÇÃO) --------

@router.post("/empresa")
def salvar_empresa(dados: EmpresaSchema, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == usuario.id).first()
        if not empresa:
            empresa = Empresa(usuario_id=usuario.id)

        empresa.nome_empresa = dados.nome_empresa
        empresa.descricao = dados.descricao
        empresa.nicho = dados.nicho
        empresa.logo_url = dados.logo_url
        empresa.funcionarios = [f.dict() for f in dados.funcionarios]
        empresa.produtos = [p.dict() for p in dados.produtos]
        empresa.redes_sociais = dados.redes_sociais
        empresa.informacoes_adicionais = dados.informacoes_adicionais
        empresa.cnpj = dados.cnpj
        empresa.rua = dados.rua
        empresa.numero = dados.numero
        empresa.bairro = dados.bairro
        empresa.cidade = dados.cidade
        empresa.cep = dados.cep
        empresa.atualizado_em = datetime.utcnow()

        db.add(empresa)
        db.commit()
        db.refresh(empresa)

        # ✅ Gera o site HTML do cliente automaticamente
        try:
            gerar_site_cliente(DadosSiteCliente(
                usuario_id=usuario.id,
                bio="",
                agendamento_ativo=False,
                horarios_disponiveis=[],
                informacoes_adicionais=dados.informacoes_adicionais
            ))
        except Exception as e:
            print(f"Erro ao gerar site do cliente: {e}")

        return {"mensagem": "Dados da empresa salvos com sucesso."}
    finally:
        db.close()

@router.get("/empresa")
def obter_empresa(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == usuario.id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada.")
        return empresa_to_dict(empresa)
    finally:
        db.close()

class EmpresaAtualizada(BaseModel):
    nome_empresa: Optional[str] = None
    descricao: Optional[str] = None
    nicho: Optional[str] = None
    logo_url: Optional[str] = None
    funcionarios: Optional[List[FuncionarioSchema]] = None
    produtos: Optional[List[ProdutoSchema]] = None
    redes_sociais: Optional[dict] = None
    informacoes_adicionais: Optional[str] = None
    cnpj: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None

@router.put("/empresa")
def atualizar_empresa(dados: EmpresaAtualizada, usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        empresa = db.query(Empresa).filter(Empresa.usuario_id == usuario.id).first()
        if not empresa:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        for campo, valor in dados.dict(exclude_unset=True).items():
            setattr(empresa, campo, valor)

        empresa.atualizado_em = datetime.utcnow()
        db.commit()
        db.refresh(empresa)

        return {"mensagem": "Empresa atualizada com sucesso."}
    finally:
        db.close()

# ✅ Geração automática de cards de marketing
@router.post("/empresa/cards_marketing")
def gerar_cards_marketing(usuario: Usuario = Depends(get_current_user)):
    db: Session = SessionLocal()
    try:
        mes_atual = datetime.utcnow().strftime("%Y-%m")
        cards_existentes = db.query(CardMarketing).filter_by(
            usuario_id=usuario.id,
            mes_referencia=mes_atual
        ).first()

        if not cards_existentes:
            exemplo_cards = [
                {
                    "titulo": "Campanha de Inauguração Digital",
                    "descricao": "Comece o mês com uma campanha de impacto nas redes sociais.",
                    "fonte": "https://exemplo.com/campanha-digital",
                    "ideias_conteudo": "1. Post teaser com contagem regressiva\n2. Reels com bastidores\n3. Cupom de boas-vindas",
                    "tipo": "Campanha"
                },
                {
                    "titulo": "Tendência: Personalização no Atendimento",
                    "descricao": "Clientes esperam um atendimento mais personalizado.",
                    "fonte": "https://exemplo.com/tendencia-atendimento",
                    "ideias_conteudo": "1. Story com nome do cliente\n2. Post com feedbacks reais\n3. Destaque mensal do cliente",
                    "tipo": "Tendência"
                }
            ]

            for item in exemplo_cards:
                card = CardMarketing(
                    usuario_id=usuario.id,
                    titulo=item["titulo"],
                    descricao=item["descricao"],
                    fonte=item["fonte"],
                    ideias_conteudo=item["ideias_conteudo"],
                    tipo=item["tipo"],
                    mes_referencia=mes_atual,
                    favorito=False,
                    eh_atualizacao=False,
                    criado_em=datetime.utcnow(),
                    atualizado_em=datetime.utcnow()
                )
                db.add(card)

            db.commit()

        return {"mensagem": "Cards de marketing gerados com sucesso."}
    finally:
        db.close()

# -------------------------------------------------------
# 🚀 ROTA: DADOS DA EMPRESA PARA O MARK (SEM LOGIN)
# -------------------------------------------------------
@router.get("/empresa_mark")
def obter_empresa_para_mark():
    """
    Rota usada exclusivamente pelo MARK IA.

    Por enquanto, para uso local e 1 usuário, ela pega
    sempre a empresa mais recentemente atualizada na tabela.
    Assim, o MARK usa SEMPRE os dados mais atuais.
    """
    db: Session = SessionLocal()
    try:
        from backend.models import Empresa  # garante import correto

        empresa = (
            db.query(Empresa)
            .order_by(Empresa.atualizado_em.desc())
            .first()
        )

        if not empresa:
            raise HTTPException(status_code=404, detail="Nenhuma empresa cadastrada.")

        return empresa_to_dict(empresa)
    finally:
        db.close()
