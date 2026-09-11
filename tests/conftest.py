from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.integrations.email import caixa_email
from app.main import app
from app.models.base import Base


@pytest.fixture(autouse=True)
def _sem_envio_real(monkeypatch) -> None:
    """Nenhum teste fala com Mailtrap ou SMTP de verdade."""
    monkeypatch.setattr(settings, "mailtrap_api_token", "")
    monkeypatch.setattr(settings, "smtp_host", "")
    caixa_email.mensagens.clear()


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    settings.jwt_secret = "segredo-de-teste-com-mais-de-32-chars"
    settings.app_env = "development"
    settings.smtp_host = ""
    settings.r2_access_key_id = ""
    settings.r2_secret_access_key = ""
    caixa_email.mensagens.clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = fabrica()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    session = fabrica()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture()
def client(db: Session) -> TestClient:
    return TestClient(app)
