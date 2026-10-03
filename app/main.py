from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.exc import TimeoutError as PoolTimeout
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import conferir_producao, settings
from app.core.database import SessionLocal, check_db, get_engine
from app.core.observabilidade import LogAcesso
from app.integrations.email import modo_envio
from app.routers.auth import router as auth_router
from app.routers.biblioteca import router as biblioteca_router
from app.routers.dev import router as dev_router
from app.routers.notificacoes import router as notificacoes_router
from app.routers.pesquisas import router as pesquisas_router
from app.routers.projetos import router as projetos_router

conferir_producao()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Seed de rótulos fora do GET (sem side effect na listagem)."""
    try:
        get_engine()
        if SessionLocal is not None:
            from app.services.projeto import garantir_rotulos

            with SessionLocal() as db:
                garantir_rotulos(db)
    except Exception:
        # Sem DATABASE_URL o /health sobe; seed fica para o 1º criar_projeto.
        pass
    yield


app = FastAPI(title="Horizon", version="0.1.0", lifespan=lifespan)


@app.exception_handler(PoolTimeout)
def pool_esgotado(_pedido: Request, _exc: PoolTimeout) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Banco ocupado. Tente novamente em instantes."},
        headers={"Retry-After": "3"},
    )

_origens = [
    origem.strip()
    for origem in settings.cors_origins.split(",")
    if origem.strip()
]
_regex = settings.cors_origin_regex.strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens,
    allow_origin_regex=_regex or None,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def inicio() -> RedirectResponse:
    return RedirectResponse(url="/app/", status_code=302)


app.add_middleware(LogAcesso)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.include_router(auth_router)
app.include_router(dev_router)
app.include_router(notificacoes_router)
app.include_router(projetos_router)
app.include_router(biblioteca_router)
app.include_router(pesquisas_router)


def incluir_lab_se_ligado() -> bool:
    """Monta /lab/* só com ENABLE_LAB. Em produção o boot já recusa o flag."""
    if not settings.enable_lab:
        return False
    for rota in app.routes:
        if getattr(rota, "path", "").startswith("/lab"):
            return True
    from app.routers.lab import router as lab_router

    app.include_router(lab_router)
    return True


incluir_lab_se_ligado()

# Frontend único: React em /app (SPA com fallback).
_react_dist = Path(__file__).resolve().parent.parent / "web" / "app"


def _arquivo_do_build(caminho: str) -> Path | None:
    """Confina o pedido dentro de web/app.

    O caminho chega da URL já decodificado, então `..` e `%2f` viram
    subida de diretório. Sem este confinamento, `/app/..%2f..%2f.env`
    devolveria segredos do servidor.
    """
    raiz = _react_dist.resolve()
    try:
        alvo = (raiz / caminho).resolve()
    except (OSError, ValueError):
        return None
    if alvo != raiz and not alvo.is_relative_to(raiz):
        return None
    return alvo


@app.get("/app")
@app.get("/app/{caminho:path}")
def spa_react(caminho: str = "") -> FileResponse:
    """Serve o build do React. Assets com extensão; demais rotas → index.html."""
    if not _react_dist.exists():
        raise HTTPException(status_code=503, detail="Frontend indisponível.")
    if caminho and "." in caminho.split("/")[-1]:
        arquivo = _arquivo_do_build(caminho)
        if arquivo is not None and arquivo.is_file():
            headers = {}
            if caminho.startswith("assets/"):
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return FileResponse(arquivo, headers=headers)
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(
        _react_dist / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/health/email")
def health_email() -> dict[str, str]:
    """Diz se o envio é Mailtrap, SMTP ou arquivo local. Sem token nem senha."""
    return {"modo": modo_envio()}


@app.get("/health")
def health() -> dict[str, str]:
    """API no ar. Não autentica e não toca no banco."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, str | int]:
    """Confirma que o Neon responde. Efeito no banco: nenhum (só SELECT 1)."""
    inicio = perf_counter()
    try:
        check_db()
    except Exception:
        # Não devolver host, senha nem o texto cru do driver.
        raise HTTPException(status_code=503, detail="banco indisponível") from None
    latencia_ms = max(0, int((perf_counter() - inicio) * 1000))
    return {"status": "ok", "latencia_ms": latencia_ms}
