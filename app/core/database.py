import threading
from collections.abc import Generator
from contextlib import AbstractContextManager, nullcontext

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine e session são criados só quando há URL. Assim o /health sobe
# mesmo sem .env, e o import da app não tenta abrir conexão.
_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def vincular_engine(engine: Engine) -> None:
    """Aponta a fábrica global para um engine já criado.

    Testes usam isto para a BackgroundTask abrir outra sessão no mesmo
    SQLite do request. Produção continua em get_engine().
    """
    global _engine, SessionLocal
    _engine = engine
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )


def desvincular_engine() -> None:
    """Solta a fábrica global. Não fecha o engine (quem criou dispõe)."""
    global _engine, SessionLocal
    _engine = None
    SessionLocal = None


def argumentos_conexao(url: str) -> dict[str, object]:
    """PgBouncer em modo transação não aceita prepared statement."""
    if "-pooler" in url:
        return {"prepare_threshold": None}
    return {}


_TRAVA_SQLITE = threading.Lock()


def serializar_no_sqlite(db: Session) -> AbstractContextManager:
    """Uma escrita por vez no SQLite dos testes, que tem uma conexão só.

    No PostgreSQL não trava nada: lá a constraint única decide.
    """
    ligacao = db.get_bind()
    if ligacao is not None and ligacao.dialect.name == "sqlite":
        return _TRAVA_SQLITE
    return nullcontext()


def aplicar_timeouts(engine: Engine, statement_ms: int, lock_ms: int) -> None:
    """Limita cada transação no PostgreSQL. Zero não instala nada."""
    if engine.dialect.name != "postgresql":
        return
    comandos = [
        f"SET LOCAL {nome} = {int(valor)}"
        for nome, valor in (
            ("statement_timeout", statement_ms),
            ("lock_timeout", lock_ms),
        )
        if int(valor) > 0
    ]
    if not comandos:
        return

    @event.listens_for(engine, "begin")
    def _limitar(conexao) -> None:
        for comando in comandos:
            conexao.exec_driver_sql(comando)


def get_engine() -> Engine:
    """Fábrica de conexões. Reutiliza o mesmo engine no processo.

    Se vincular_engine já definiu o engine, devolve esse — sem exigir
    DATABASE_URL. Assim o teste não cai no Neon.
    """
    global _engine, SessionLocal
    if _engine is not None:
        return _engine
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurada")
    _engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=settings.db_pool_timeout,
        connect_args=argumentos_conexao(settings.database_url),
    )
    aplicar_timeouts(
        _engine, settings.db_statement_timeout_ms, settings.db_lock_timeout_ms
    )
    SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
    )
    return _engine


def get_db() -> Generator[Session, None, None]:
    """Uma session por request. Fecha sempre, mesmo se a rota falhar."""
    get_engine()
    if SessionLocal is None:
        raise RuntimeError("session não inicializada")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db() -> None:
    """SELECT 1. Não cria tabela, não grava e não lê dado de negócio."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
