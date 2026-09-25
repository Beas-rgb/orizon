"""Medição de carga: percentis e recusa de URL de produção."""

from __future__ import annotations

from statistics import mean
from urllib.parse import urlparse

PASSOS = (10, 20, 50, 100, 200, 300)
HOSPEDES_PRODUCAO = (
    "orizon-api.onrender.com",
    "orizon.onrender.com",
    "api.orizon.app",
    "orizon.app",
)


def recusar_producao(url: str) -> None:
    host = urlparse(url).netloc.lower().split(":")[0]
    if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return
    if "staging" in host or host.endswith(".local"):
        return
    if host in HOSPEDES_PRODUCAO or host.endswith("onrender.com"):
        raise SystemExit("Recusado: esta URL parece produção. Use staging.")


def percentis(amostras: list[float]) -> dict[str, float]:
    if not amostras:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "media": 0.0}
    ordenadas = sorted(amostras)
    n = len(ordenadas)

    def p(q: float) -> float:
        idx = min(n - 1, max(0, int(round((q / 100) * (n - 1)))))
        return round(ordenadas[idx], 3)

    return {
        "p50": p(50),
        "p95": p(95),
        "p99": p(99),
        "media": round(mean(ordenadas), 3),
    }


def resumo_passo(
    n: int,
    duracoes_ms: list[float],
    erros: int,
    segundos: float,
) -> dict[str, float | int]:
    ok = len(duracoes_ms)
    total = ok + erros
    rps = round(total / segundos, 2) if segundos > 0 else 0.0
    taxa_erro = round((erros / total) * 100, 2) if total else 0.0
    return {
        "n": n,
        "ok": ok,
        "erros": erros,
        "erro_pct": taxa_erro,
        "rps": rps,
        **percentis(duracoes_ms),
    }
