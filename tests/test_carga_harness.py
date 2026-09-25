"""Harness de carga: percentis e um passo local no TestClient."""

import time

from scripts.carga_lib import PASSOS, percentis, recusar_producao, resumo_passo


def test_percentis_basicos() -> None:
    dados = percentis([10, 20, 30, 40, 50])
    assert dados["p50"] == 30
    assert dados["p99"] >= dados["p95"] >= dados["p50"]
    assert dados["media"] == 30


def test_recusar_producao_localhost() -> None:
    recusar_producao("http://127.0.0.1:8000/health")
    recusar_producao("http://localhost:8000/health")


def test_recusar_producao_render() -> None:
    try:
        recusar_producao("https://orizon-api.onrender.com/health")
    except SystemExit as exc:
        assert "produção" in str(exc)
    else:
        raise AssertionError("deveria recusar produção")


def test_passo_local_health(client) -> None:
    duracoes: list[float] = []
    erros = 0
    n = PASSOS[0]
    inicio = time.perf_counter()
    for _ in range(n):
        t0 = time.perf_counter()
        resp = client.get("/health")
        if resp.status_code >= 400:
            erros += 1
        else:
            duracoes.append((time.perf_counter() - t0) * 1000)
    linha = resumo_passo(n, duracoes, erros, time.perf_counter() - inicio)
    assert linha["ok"] == n
    assert linha["erro_pct"] == 0
    assert linha["p99"] >= linha["p50"]
