"""A limpeza só leva o que já venceu."""

from datetime import UTC, datetime, timedelta

from app.core.tokens import novo_id
from app.models.sessao import Sessao
from app.services.manutencao import limpar_tabelas


def test_limpa_sessao_vencida_e_preserva_a_ativa(db) -> None:
    from app.models.base import agora
    from app.models.usuario import Usuario

    pessoa = Usuario(
        id=novo_id(),
        nome="Ana",
        email="ana-limpeza@horizon.dev",
        senha_hash=None,
        papel="FUNCIONARIO",
        ativo=True,
        tentativas_falhas=0,
        criado_em=agora(),
        atualizado_em=agora(),
        deleted_at=None,
    )
    db.add(pessoa)
    db.flush()
    momento = datetime.now(UTC)
    velha = Sessao(
        id=novo_id(),
        usuario_id=pessoa.id,
        token_hash="a" * 64,
        expira_em=momento - timedelta(days=10),
        revogado_em=momento - timedelta(days=10),
        criado_em=momento - timedelta(days=11),
    )
    viva = Sessao(
        id=novo_id(),
        usuario_id=pessoa.id,
        token_hash="b" * 64,
        expira_em=momento + timedelta(days=1),
        revogado_em=None,
        criado_em=momento,
    )
    db.add(velha)
    db.add(viva)
    db.commit()
    saida = limpar_tabelas(db, momento, lote=10)
    db.commit()
    assert saida["sessoes"] == 1
    restantes = db.query(Sessao).all()
    assert [item.id for item in restantes] == [viva.id]
