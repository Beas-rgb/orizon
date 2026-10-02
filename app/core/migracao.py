"""Sobe a revisão só quando ela mudou. `python -m app.core.migracao`."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import settings

TRAVA = 727274


def url_direta(database_url: str, direta: str = "") -> str:
    """Prefere a URL direta. Tira `-pooler` do host quando ela não vier pronta."""
    if direta.strip():
        return direta.strip()
    return database_url.replace("-pooler", "", 1)


def eh_postgres(url: str) -> bool:
    return url.startswith("postgres")


def aplicar(
    atual: str | None,
    esperada: str,
    url: str,
    upgrade,
    travar,
) -> str:
    """Igual: não migra. Postgres trava antes. SQLite não usa advisory lock."""
    if atual == esperada:
        return "migracoes em dia"
    if eh_postgres(url):
        travar()
    upgrade()
    return "atualizada"


def _revisao_esperada() -> str:
    candidatos = [
        Path("/app/ALEMBIC_HEAD"),
        Path(__file__).resolve().parents[2] / "ALEMBIC_HEAD",
    ]
    for caminho in candidatos:
        if caminho.is_file():
            return caminho.read_text(encoding="utf-8").strip().split()[0]
    raise SystemExit("ALEMBIC_HEAD ausente. O build da imagem deve gerá-lo.")


def _revisao_atual(url: str) -> str | None:
    engine = create_engine(url)
    with engine.connect() as conexao:
        try:
            return conexao.execute(
                text("select version_num from alembic_version")
            ).scalar()
        except Exception:
            return None


def _travar(url: str):
    engine = create_engine(url)
    conexao = engine.connect()
    conexao.execute(text(f"SELECT pg_advisory_lock({TRAVA})"))
    conexao.commit()
    return conexao


def _soltar(conexao) -> None:
    conexao.execute(text(f"SELECT pg_advisory_unlock({TRAVA})"))
    conexao.commit()
    conexao.close()


def _upgrade(url: str) -> None:
    anterior = settings.database_url
    settings.database_url = url
    try:
        comando = Config("alembic.ini")
        command.upgrade(comando, "head")
    finally:
        settings.database_url = anterior


def main() -> int:
    esperada = _revisao_esperada()
    url = url_direta(settings.database_url, settings.database_url_direct)
    atual = _revisao_atual(url)
    trava = None

    def travar() -> None:
        nonlocal trava
        trava = _travar(url)

    try:
        resultado = aplicar(atual, esperada, url, lambda: _upgrade(url), travar)
    finally:
        if trava is not None:
            _soltar(trava)
    print(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
