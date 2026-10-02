from app.core.migracao import aplicar, eh_postgres, url_direta


def test_url_direta_tira_pooler() -> None:
    origem = "postgresql://u:p@ep-abc-pooler.neon.tech/db"
    assert url_direta(origem) == "postgresql://u:p@ep-abc.neon.tech/db"
    assert url_direta(origem, "postgresql://u:p@ep-abc.neon.tech/db") == (
        "postgresql://u:p@ep-abc.neon.tech/db"
    )


def test_cabeca_igual_nao_migra() -> None:
    chamadas: list[str] = []
    resultado = aplicar(
        "0017_avaliacao_resposta",
        "0017_avaliacao_resposta",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
    )
    assert resultado == "migracoes em dia"
    assert chamadas == []


def test_cabeca_diferente_migra_uma_vez() -> None:
    chamadas: list[str] = []
    resultado = aplicar(
        None,
        "0017_avaliacao_resposta",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
    )
    assert resultado == "atualizada"
    assert chamadas == ["up"]


def test_sqlite_nao_trava() -> None:
    assert eh_postgres("sqlite://") is False
    chamadas: list[str] = []
    aplicar(
        "antiga",
        "nova",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
    )
    assert chamadas == ["up"]


def test_postgres_trava_antes_de_migrar() -> None:
    assert eh_postgres("postgresql://h/db") is True
    chamadas: list[str] = []
    aplicar(
        "antiga",
        "nova",
        "postgresql://h/db",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
    )
    assert chamadas == ["lock", "up"]
