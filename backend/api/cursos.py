from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional



from backend.database import SessionLocal
from backend.models import Usuario
from backend.models.curso import (
    Curso,
    Aula,
    CompraCurso,
    ProgressoCurso,
    CupomDesconto,
    PagamentoCurso,  # importante para registrar pagamentos pendentes
)
from backend.api.auth import get_current_user

router = APIRouter(prefix="/cursos", tags=["Cursos"])


# ---------------------- Conexão com o banco ----------------------


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------- Schemas ----------------------


class AulaSchema(BaseModel):
    id: int
    titulo: str
    descricao: str
    video_url: str
    ordem: int

    class Config:
        orm_mode = True

class AulaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    video_url: Optional[str] = None
    ordem: Optional[int] = None

    class Config:
        orm_mode = True



class CursoSchema(BaseModel):
    id: int
    titulo: str
    descricao: str
    capa_url: Optional[str]
    categoria: Optional[str]
    gratuito: bool
    preco: Optional[float]
    destaque: bool
    aulas: List[AulaSchema] = []
    ordem: Optional[int] = None  # 👈 ADICIONAR

    class Config:
        orm_mode = True


class CursoCreate(BaseModel):
    titulo: str
    descricao: str
    capa_url: Optional[str] = None
    categoria: Optional[str] = None
    gratuito: bool = True
    preco: Optional[float] = None
    destaque: bool = False
    ativo: bool = True
    ordem: Optional[int] = None  # 👈 ADICIONAR


# ---------------------- Rotas públicas ----------------------


@router.get("/progresso")
def progresso_usuario(
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna a lista de IDs de aulas concluídas pelo usuário logado.
    """
    progresso = db.query(ProgressoCurso).filter_by(usuario_id=usuario.id).all()
    ids_concluidos = [p.aula_id for p in progresso]
    return {"aulas_concluidas": ids_concluidos}


@router.get("/", response_model=List[CursoSchema])
def listar_cursos(db: Session = Depends(get_db)):
    """
    Lista todos os cursos ativos.
    """
    return db.query(Curso).filter(Curso.ativo == True).all()


@router.get("/{curso_id}", response_model=CursoSchema)
def detalhes_curso(curso_id: int, db: Session = Depends(get_db)):
    """
    Retorna detalhes de um curso específico, incluindo aulas.
    """
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")
    return curso


# ---------------------- Compra e progresso ----------------------


@router.post("/{curso_id}/comprar")
def comprar_curso(
    curso_id: int,
    cupom: Optional[str] = None,
    metodo: Optional[str] = "pix",  # 'pix' ou 'cartao'
    gateway: Optional[str] = "infinitepay",
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    curso = (
        db.query(Curso)
        .filter(Curso.id == curso_id, Curso.ativo == True)
        .first()
    )
    if not curso:
        raise HTTPException(status_code=404, detail="Curso inválido.")

    # Já comprado ou gratuito?
    ja_tem = (
        db.query(CompraCurso)
        .filter_by(usuario_id=usuario.id, curso_id=curso_id)
        .first()
    )
    if ja_tem or curso.gratuito:
        return {"mensagem": "Curso já liberado."}

    valor = float(curso.preco or 0.0)

    # Aplica cupom
    if cupom:
        c = db.query(CupomDesconto).filter_by(codigo=cupom, ativo=True).first()
        if not c:
            raise HTTPException(status_code=400, detail="Cupom inválido.")
        if c.validade and c.validade < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Cupom expirado.")
        if c.curso_id and c.curso_id != curso.id:
            raise HTTPException(
                status_code=400,
                detail="Cupom não válido para este curso.",
            )
        valor *= (1 - c.percentual / 100)

    # Se valor final for 0, libera na hora
    if valor <= 0.01:
        compra = CompraCurso(
            usuario_id=usuario.id,
            curso_id=curso.id,
            preco_pago=0.0,
        )
        db.add(compra)
        db.commit()
        return {"mensagem": "Curso liberado com cupom de 100%."}

    # Caso contrário, registra pagamento pendente
    pagamento = PagamentoCurso(
        usuario_id=usuario.id,
        curso_id=curso.id,
        status="pendente",
        valor=valor,
        metodo=metodo,
        gateway=gateway,
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    return {
        "mensagem": "Pagamento pendente",
        "pagamento_id": pagamento.id,
        "valor": float(valor),
        "status": "aguardando",
    }


@router.post("/aula/{aula_id}/concluir")
def concluir_aula(
    aula_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marca uma aula como concluída para o usuário atual.
    """
    registro = ProgressoCurso(usuario_id=usuario.id, aula_id=aula_id)
    db.add(registro)
    db.commit()
    return {"mensagem": "Aula marcada como concluída"}


# ---------------------- Área administrativa ----------------------


@router.post("/admin/curso")
def criar_curso(
    curso: CursoCreate,
    db: Session = Depends(get_db),
):
    # se não vier ordem, joga para o final
    ordem = curso.ordem
    if ordem is None:
        max_ordem = db.query(Curso).order_by(Curso.ordem.desc()).first()
        ordem = (max_ordem.ordem + 1) if max_ordem and max_ordem.ordem is not None else 1

    novo = Curso(
        titulo=curso.titulo,
        descricao=curso.descricao,
        capa_url=curso.capa_url,
        categoria=curso.categoria,
        gratuito=curso.gratuito,
        preco=curso.preco,
        destaque=curso.destaque,
        ativo=curso.ativo,
        criado_em=datetime.utcnow(),
        ordem=ordem,  # 👈 novo
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "mensagem": "Curso criado com sucesso!"}



@router.post("/admin/aula")
def criar_aula(aula: dict, db: Session = Depends(get_db)):
    nova = Aula(
        curso_id=aula["curso_id"],
        titulo=aula["titulo"],
        descricao=aula["descricao"],
        video_url=aula["video_url"],
        ordem=aula["ordem"],
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {"mensagem": "Aula criada com sucesso", "id": nova.id}

@router.put("/admin/aula/{aula_id}")
def atualizar_aula(
    aula_id: int,
    dados: AulaUpdate,
    db: Session = Depends(get_db),
):
    """
    Atualiza título, descrição, vídeo e/ou ordem de uma aula específica.
    """
    aula = db.query(Aula).filter_by(id=aula_id).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula não encontrada.")

    # Só atualiza os campos que vierem preenchidos
    campos = dados.dict(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(aula, campo, valor)

    db.commit()
    db.refresh(aula)
    return {"mensagem": "Aula atualizada com sucesso", "id": aula.id}



@router.post("/admin/cupom")
def criar_cupom(cupom: dict, db: Session = Depends(get_db)):
    novo = CupomDesconto(
        codigo=cupom["codigo"],
        descricao=cupom["descricao"],
        percentual=cupom["percentual"],
        curso_id=cupom.get("curso_id"),
        validade=(
            datetime.strptime(cupom["validade"], "%Y-%m-%d")
            if cupom.get("validade")
            else None
        ),
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"mensagem": "Cupom criado com sucesso", "id": novo.id}


@router.put("/{curso_id}")
def atualizar_curso(
    curso_id: int,
    dados: CursoCreate,
    db: Session = Depends(get_db),
):
    curso = db.query(Curso).filter_by(id=curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    for campo, valor in dados.dict().items():
        setattr(curso, campo, valor)

    db.commit()
    db.refresh(curso)
    return {"mensagem": "Curso atualizado com sucesso!"}
