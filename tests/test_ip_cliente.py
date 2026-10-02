from fastapi import Request

from app.core.cliente import ip_do_cliente
from app.core.config import settings
from tests.contas import abrir_consultora


def _pedido(xff: str | None = None) -> Request:
    cabecalhos = []
    if xff is not None:
        cabecalhos.append((b"x-forwarded-for", xff.encode()))
    escopo = {
        "type": "http",
        "headers": cabecalhos,
        "client": ("10.0.0.8", 1234),
    }
    return Request(escopo)


def test_hops_zero_ignora_xff(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    assert ip_do_cliente(_pedido("1.2.3.4, 10.0.0.8")) == "10.0.0.8"


def test_xff_forjado_nao_muda_o_ip_com_um_salto(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert ip_do_cliente(_pedido("1.2.3.4, 203.0.113.9")) == "203.0.113.9"


def test_valor_invalido_cai_no_host(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert ip_do_cliente(_pedido("nao-e-ip")) == "10.0.0.8"


def test_diagnostico_de_ip_so_para_ti(client) -> None:
    from tests.contas import SENHA

    consultora = abrir_consultora(client, email="c-ip@horizon.dev")
    dev = client.post(
        "/auth/login",
        json={"email": "joao@horizon.dev", "senha": SENHA},
    )
    ti = {"Authorization": f"Bearer {dev.json()['access_token']}"}
    ok = client.get(
        "/dev/diagnostico/ip",
        headers={**ti, "X-Forwarded-For": "1.1.1.1"},
    )
    assert ok.status_code == 200
    assert ok.json()["client_host"]
    assert "x-forwarded-for" in ok.json()
    negado = client.get("/dev/diagnostico/ip", headers=consultora)
    assert negado.status_code == 404
