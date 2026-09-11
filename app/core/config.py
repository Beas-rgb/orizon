import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lê configuração do ambiente. Segredos ficam no .env, nunca no código."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    app_env: str = "development"

    # Neon: poucas conexões simultâneas. Sem overflow para não estourar a cota.
    db_pool_size: int = 5
    db_max_overflow: int = 0

    jwt_secret: str = ""
    jwt_access_minutos: int = 15
    jwt_refresh_dias: int = 7

    # Força bruta: 3 erros e a chave espera 5 minutos. Gravado no banco.
    login_max_tentativas: int = 3
    login_espera_minutos: int = 5

    app_public_url: str = "http://127.0.0.1:8000/app"

    # Origens do front, separadas por vírgula. Sem isto o navegador
    # bloqueia a tela hospedada de chamar a API (CORS).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Mailtrap Email API. O token é segredo; o remetente é valor de setup.
    mailtrap_api_token: str = ""
    mailtrap_from_email: str = ""
    mailtrap_from_name: str = "Horizon"

    r2_account_id: str = ""
    r2_endpoint: str = ""
    r2_bucket: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""

    # Conta do TI. A senha fica só no .env; no banco entra o hash.
    admin_nome: str = ""
    admin_email: str = ""
    admin_senha: str = ""

    def __repr__(self) -> str:
        return "Settings(segredos ocultos)"

    def __str__(self) -> str:
        return "Settings(segredos ocultos)"


settings = Settings()


def url_publica() -> str:
    """Endereço da tela. No Render usa o host público, não o localhost."""
    externa = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    atual = settings.app_public_url.rstrip("/")
    if externa and (
        not atual or "127.0.0.1" in atual or "localhost" in atual
    ):
        return f"{externa}/app"
    return atual
