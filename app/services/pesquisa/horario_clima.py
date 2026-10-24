"""Horário único do clima: a meia-noite UTC do dia em que a pesquisa foi publicada.

Não é o instante de cada envio. O desempenho não passa por aqui.
"""

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


def _como_data(valor: datetime | str | None) -> datetime | None:
    if valor is None or isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def instante_fixo(momento: datetime | str | None) -> datetime:
    base = _como_data(momento) or datetime.now(UTC)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    else:
        base = base.astimezone(UTC)
    return datetime(base.year, base.month, base.day, tzinfo=UTC)


def limpar_horarios_clima(conexao: Session) -> None:
    """Apaga o carimbo individual do clima já gravado. Não restaura no downgrade."""
    pesquisas = conexao.execute(
        text(
            "SELECT id, publicada_em, criado_em FROM pesquisas WHERE tipo = 'CLIMA'"
        )
    ).all()
    for pesquisa_id, publicada_em, criado_em in pesquisas:
        fixa = instante_fixo(_como_data(publicada_em) or _como_data(criado_em))
        conexao.execute(
            text(
                """
                UPDATE tokens_resposta
                SET criado_em = :fixa, usado_em = NULL
                WHERE pesquisa_id = :id
                """
            ),
            {"fixa": fixa, "id": pesquisa_id},
        )
        conexao.execute(
            text(
                """
                UPDATE respostas
                SET respondido_em = :fixa
                WHERE token_id IN (
                    SELECT id FROM tokens_resposta WHERE pesquisa_id = :id
                )
                """
            ),
            {"fixa": fixa, "id": pesquisa_id},
        )
        conexao.execute(
            text(
                """
                UPDATE pesquisa_participantes
                SET iniciado_em = NULL,
                    respondido_em = NULL,
                    atualizado_em = criado_em
                WHERE pesquisa_id = :id
                """
            ),
            {"id": pesquisa_id},
        )
