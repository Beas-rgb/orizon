"""Constantes e helpers compartilhados do domínio pesquisa."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pesquisa import OpcaoResposta, Pesquisa
from app.services.identidade import ErroAuth

TIPOS = {"CLIMA", "DESEMPENHO", "CARGOS_SALARIOS", "PERSONALIZADA"}
TIPOS_PERGUNTA = {
    "TEXTO_LIVRE",
    "NOTA_5",
    "NOTA_10",
    "SIM_NAO",
    "MULTIPLA_ESCOLHA",
    "CHECKBOX",
}
RESPONDER_MAX_TENTATIVAS = 10
RESPONDER_JANELA_MINUTOS = 5
# Painel omite média/distribuição quando há menos respondentes distintos.
K_ANONIMATO = 5
TIPOS_ANONIMOS = {"CLIMA"}


def _ciente(valor):
    if valor is None:
        return None
    if valor.tzinfo is None:
        from datetime import UTC

        return valor.replace(tzinfo=UTC)
    return valor


def _pesquisa_viva(db: Session, pesquisa_id: str) -> Pesquisa:
    pesquisa = db.get(Pesquisa, pesquisa_id)
    if pesquisa is None or pesquisa.deleted_at is not None:
        raise ErroAuth(404, "Pesquisa não encontrada.")
    return pesquisa


def opcoes_da(db: Session, pergunta_id: str) -> list[OpcaoResposta]:
    return list(
        db.scalars(
            select(OpcaoResposta)
            .where(OpcaoResposta.pergunta_id == pergunta_id)
            .order_by(OpcaoResposta.ordem)
        ).all()
    )
