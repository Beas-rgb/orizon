from app.core.migracao import aplicar, eh_postgres, url_direta

GRAFO = {
    "conhecidas": {"0001_baseline", "0020_lab", "0021_indices_modelo"},
    "ancestrais": {"0001_baseline", "0020_lab"},
}


def test_url_direta_tira_pooler() -> None:
    origem = "postgresql://u:p@ep-abc-pooler.neon.tech/db"
    assert url_direta(origem) == "postgresql://u:p@ep-abc.neon.tech/db"
    assert url_direta(origem, "postgresql://u:p@ep-abc.neon.tech/db") == (
        "postgresql://u:p@ep-abc.neon.tech/db"
    )


def test_cabeca_igual_nao_migra() -> None:
    chamadas: list[str] = []
    resultado = aplicar(
        "0021_indices_modelo",
        "0021_indices_modelo",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
        **GRAFO,
    )
    assert resultado == "migracoes em dia"
    assert chamadas == []


def test_banco_vazio_instala_uma_vez() -> None:
    chamadas: list[str] = []
    resultado = aplicar(
        None,
        "0021_indices_modelo",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
        **GRAFO,
    )
    assert resultado == "atualizada"
    assert chamadas == ["up"]


def test_sqlite_nao_trava() -> None:
    assert eh_postgres("sqlite://") is False
    chamadas: list[str] = []
    aplicar(
        "0020_lab",
        "0021_indices_modelo",
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
        autorizadas=frozenset({"0020_lab"}),
        **GRAFO,
    )
    assert chamadas == ["up"]


def test_postgres_trava_antes_de_migrar() -> None:
    assert eh_postgres("postgresql://h/db") is True
    chamadas: list[str] = []
    aplicar(
        "0020_lab",
        "0021_indices_modelo",
        "postgresql://h/db",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
        autorizadas=frozenset({"0020_lab"}),
        **GRAFO,
    )
    assert chamadas == ["lock", "up"]
