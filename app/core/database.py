from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine e session são criados só quando há URL. Assim o /health sobe
# mesmo sem .env, e o import da app não tenta abrir conexão.
_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Fábrica de conexões. Reutiliza o mesmo engine no processo."""
    global _engine, SessionLocal
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL não configurada")
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
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
