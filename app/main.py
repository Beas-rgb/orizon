from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import check_db
from app.core.observabilidade import LogAcesso
from app.routers.auth import router as auth_router
from app.routers.biblioteca import router as biblioteca_router
from app.routers.notificacoes import router as notificacoes_router
from app.routers.pesquisas import router as pesquisas_router
from app.routers.projetos import router as projetos_router

app = FastAPI(title="Horizon", version="0.1.0")

_origens = [origem.strip() for origem in settings.cors_origins.split(",") if origem.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    allow_origin_regex=r"https://([a-z0-9-]+\.)?orizon-a0u\.pages\.dev",
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def inicio() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=302)
app.add_middleware(LogAcesso)
app.include_router(auth_router)
app.include_router(notificacoes_router)
app.include_router(projetos_router)
app.include_router(biblioteca_router)
app.include_router(pesquisas_router)
app.mount(
    "/app",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "web", html=True),
    name="app",
)


@app.get("/health/email")
def health_email() -> dict[str, str]:
    """Diz se o envio é real ou arquivo local. Não devolve senha nem host."""
    from app.core.config import settings

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        return {"modo": "smtp"}
    return {"modo": "local"}


@app.get("/health")
def health() -> dict[str, str]:
    """API no ar. Não autentica e não toca no banco."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, str]:
    """Confirma que o Neon responde. Efeito no banco: nenhum (só SELECT 1)."""
    try:
        check_db()
    except Exception:
        # Não devolver host, senha nem o texto cru do driver.
        raise HTTPException(status_code=503, detail="banco indisponível") from None
    return {"status": "ok"}
