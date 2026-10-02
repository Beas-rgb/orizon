import gzip
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.gzip import GZipMiddleware

from app.main import app


def test_app_usa_gzip() -> None:
    nomes = [item.cls.__name__ for item in app.user_middleware]
    assert "GZipMiddleware" in nomes


def test_json_grande_sai_gzip() -> None:
    mini = FastAPI()
    mini.add_middleware(GZipMiddleware, minimum_size=1024)

    @mini.get("/grande")
    def grande() -> dict:
        return {"texto": "a" * 2000}

    resposta = TestClient(mini).get("/grande", headers={"Accept-Encoding": "gzip"})
    assert resposta.status_code == 200
    assert resposta.headers.get("content-encoding") == "gzip"
    assert len(gzip.compress(resposta.content)) < 2000 or resposta.content


def test_asset_com_hash_tem_cache_imutavel() -> None:
    assets = list(Path("web/app/assets").glob("*.js"))
    assert assets
    resposta = TestClient(app).get(f"/app/assets/{assets[0].name}")
    assert resposta.status_code == 200
    assert "immutable" in resposta.headers["cache-control"]


def test_html_nao_fica_em_cache() -> None:
    resposta = TestClient(app).get("/app/login")
    assert "no-cache" in resposta.headers["cache-control"]
