"""Painel do dev. Autoriza conta de consultora. Não devolve senha nem token."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.services.identidade import (
    ErroAuth,
    autorizar_pedido,
    diagnostico,
    listar_consultores,
    listar_pedidos,
    pedir_conta_consultora,
    reenviar_primeiro_acesso_consultora,
)

router = APIRouter(tags=["dev"])


class CadastroConsultora(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=255)


class PedidoSaida(BaseModel):
    id: str
    nome: str
    email: str
    status: str
    expira_em: datetime


class ConsultoraSaida(BaseModel):
    id: str
    nome: str
    email: str
    ativo: bool


class MensagemSaida(BaseModel):
    mensagem: str
    email: str | None = None
    link_primeiro_acesso: str | None = None


def _chamar(acao):
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


@router.post("/auth/cadastro-consultora", response_model=MensagemSaida)
def cadastrar(
    corpo: CadastroConsultora,
    db: Session = Depends(get_db),
) -> MensagemSaida:
    """Pedido público. Não cria login e não devolve token."""
    _chamar(lambda: pedir_conta_consultora(db, corpo.nome, corpo.email))
    return MensagemSaida(
        mensagem="Pedido registrado. A conta só nasce depois da autorização."
    )


@router.get("/dev/pedidos", response_model=list[PedidoSaida])
def pedidos(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PedidoSaida]:
    itens = _chamar(lambda: listar_pedidos(db, usuario))
    return [
        PedidoSaida(
            id=item.id,
            nome=item.nome,
            email=item.email,
            status=item.status,
            expira_em=item.expira_em,
        )
        for item in itens
    ]


@router.get("/dev/consultores", response_model=list[ConsultoraSaida])
def consultores(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[ConsultoraSaida]:
    itens = _chamar(lambda: listar_consultores(db, usuario))
    return [
        ConsultoraSaida(
            id=item.id,
            nome=item.nome,
            email=item.email,
            ativo=item.ativo,
        )
        for item in itens
    ]


@router.get("/dev/diagnostico")
def analise(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Estabilidade da API. Só o TI. Sem senha, host nem URL de banco."""
    return _chamar(lambda: diagnostico(db, usuario))


@router.post("/dev/pedidos/{pedido_id}/autorizar", response_model=MensagemSaida)
def autorizar(
    pedido_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> MensagemSaida:
    """Cria a conta sem senha e envia o primeiro acesso ao e-mail cadastrado."""
    saida = _chamar(lambda: autorizar_pedido(db, usuario, pedido_id))
    return MensagemSaida(**saida)


@router.post(
    "/dev/consultores/{consultor_id}/reenviar-primeiro-acesso",
    response_model=MensagemSaida,
)
def reenviar_primeiro_acesso(
    consultor_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> MensagemSaida:
    """Novo token se a consultora ainda não criou senha.

    Em dev o link volta na resposta.
    """
    saida = _chamar(
        lambda: reenviar_primeiro_acesso_consultora(db, usuario, consultor_id)
    )
    return MensagemSaida(**saida)
