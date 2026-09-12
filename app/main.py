from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import settings
from app.core.database import check_db
from app.core.observabilidade import LogAcesso
from app.integrations.email import modo_envio
from app.routers.auth import router as auth_router
from app.routers.biblioteca import router as biblioteca_router
from app.routers.dev import router as dev_router
from app.routers.notificacoes import router as notificacoes_router
from app.routers.pesquisas import router as pesquisas_router
from app.routers.projetos import router as projetos_router

app = FastAPI(title="Horizon", version="0.1.0")

_origens = [
    origem.strip()
    for origem in settings.cors_origins.split(",")
    if origem.strip()
]
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
app.include_router(dev_router)
app.include_router(notificacoes_router)
app.include_router(projetos_router)
app.include_router(biblioteca_router)
app.include_router(pesquisas_router)

# Frontend único: React em /app (SPA com fallback).
_react_dist = Path(__file__).resolve().parent.parent / "web" / "app"


@app.get("/app")
@app.get("/app/{caminho:path}")
def spa_react(caminho: str = "") -> FileResponse:
    """Serve o build do React. Assets com extensão; demais rotas → index.html."""
    if not _react_dist.exists():
        raise HTTPException(status_code=503, detail="Frontend indisponível.")
    if caminho and "." in caminho.split("/")[-1]:
        arquivo = _react_dist / caminho
        if arquivo.is_file():
            return FileResponse(arquivo)
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(_react_dist / "index.html")


@app.get("/health/email")
def health_email() -> dict[str, str]:
    """Diz se o envio é Mailtrap, SMTP ou arquivo local. Sem token nem senha."""
    return {"modo": modo_envio()}


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
