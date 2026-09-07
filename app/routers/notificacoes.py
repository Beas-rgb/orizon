"""Avisos da própria conta. Conhecer o ID de outro usuário não abre o aviso."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.schemas.notificacao import EntregaSaida, NotificacaoSaida
from app.services.identidade import ErroAuth
from app.services.notificacao import listar, listar_entregas, marcar_lida

router = APIRouter(tags=["notificacoes"])


def _chamar(acao):
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


def _aviso(item) -> NotificacaoSaida:
    return NotificacaoSaida(
        id=item.id,
        tipo=item.tipo,
        titulo=item.titulo,
        mensagem=item.mensagem,
        lida=item.lida,
        projeto_id=item.projeto_id,
        criado_em=item.criado_em,
    )


@router.get("/notificacoes", response_model=list[NotificacaoSaida])
def listar_avisos(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[NotificacaoSaida]:
    """Só os avisos deste login. Não lista a caixa de outra pessoa."""
    return [_aviso(item) for item in listar(db, usuario)]


@router.post("/notificacoes/{aviso_id}/lida", response_model=NotificacaoSaida)
def lida(
    aviso_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> NotificacaoSaida:
    """Marca como lido. Aviso de outra conta responde 404."""
    aviso = _chamar(lambda: marcar_lida(db, usuario, aviso_id))
    return _aviso(aviso)


@router.get("/projetos/{projeto_id}/entregas", response_model=list[EntregaSaida])
def entregas(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[EntregaSaida]:
    """A consultora vê o status do envio. Sem corpo do e-mail e sem token."""
    itens = _chamar(lambda: listar_entregas(db, usuario, projeto_id))
    return [
        EntregaSaida(
            id=item.id,
            canal=item.canal,
            destino=item.destino,
            assunto=item.assunto,
            status=item.status,
            referencia=item.referencia,
            criado_em=item.criado_em,
        )
        for item in itens
    ]
