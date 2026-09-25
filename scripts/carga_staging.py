"""Carga progressiva 10→300. Só staging ou localhost.

Uso:
  HORIZON_AMBIENTE=staging HORIZON_CARGA_URL=https://staging... \\
    python scripts/carga_staging.py

  python scripts/carga_staging.py --local   # http://127.0.0.1:8000/health
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.carga_lib import PASSOS, recusar_producao, resumo_passo


def _url_alvo() -> str:
    if "--testclient" in sys.argv:
        return "testclient://health"
    if "--local" in sys.argv:
        return os.environ.get("HORIZON_CARGA_URL", "http://127.0.0.1:8000/health")
    ambiente = os.environ.get("HORIZON_AMBIENTE", "")
    if ambiente != "staging":
        raise SystemExit("Defina HORIZON_AMBIENTE=staging ou use --local.")
    url = os.environ.get("HORIZON_CARGA_URL", "").strip()
    if not url:
        raise SystemExit("Defina HORIZON_CARGA_URL do staging.")
    recusar_producao(url)
    if url.endswith("/health") or "/health" in url:
        return url
    return url.rstrip("/") + "/health"


def _bater(url: str, token: str) -> float:
    inicio = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"HTTP {resp.status}")
    return (time.perf_counter() - inicio) * 1000


def _passo(url: str, token: str, n: int) -> dict[str, float | int]:
    duracoes: list[float] = []
    erros = 0
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(n, 40)) as pool:
        futuros = [pool.submit(_bater, url, token) for _ in range(n)]
        for fut in as_completed(futuros):
            try:
                duracoes.append(fut.result())
            except (urllib.error.URLError, TimeoutError, RuntimeError, OSError):
                erros += 1
    return resumo_passo(n, duracoes, erros, time.perf_counter() - inicio)


def _passo_testclient(n: int) -> dict[str, float | int]:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    duracoes: list[float] = []
    erros = 0
    inicio = time.perf_counter()
    for _ in range(n):
        t0 = time.perf_counter()
        resp = client.get("/health")
        if resp.status_code >= 400:
            erros += 1
        else:
            duracoes.append((time.perf_counter() - t0) * 1000)
    return resumo_passo(n, duracoes, erros, time.perf_counter() - inicio)


def main() -> None:
    url = _url_alvo()
    token = os.environ.get("HORIZON_CARGA_TOKEN", "")
    print("alvo", url.split("://")[0], "passos", ",".join(str(p) for p in PASSOS))
    for n in PASSOS:
        if url.startswith("testclient"):
            linha = _passo_testclient(n)
        else:
            linha = _passo(url, token, n)
        print(
            f"n={linha['n']} ok={linha['ok']} erro%={linha['erro_pct']} "
            f"rps={linha['rps']} p50={linha['p50']} p95={linha['p95']} "
            f"p99={linha['p99']}"
        )


if __name__ == "__main__":
    main()
