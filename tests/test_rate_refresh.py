"""Refresh inválido: três falhas e a quarta espera 5 minutos."""

from tests.contas import SENHA, abrir_consultora


def test_refresh_invalido_trava_na_quarta(client) -> None:
    for indice in range(3):
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": f"invalido-{indice}-xxxx"},
        )
        assert resp.status_code == 401
    quarto = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalido-3-xxxx"},
    )
    assert quarto.status_code == 429


def test_refresh_valido_zera_o_contador(client) -> None:
    headers = abrir_consultora(client)
    email = client.get("/auth/eu", headers=headers).json()["email"]
    entrada = client.post("/auth/login", json={"email": email, "senha": SENHA})
    assert entrada.status_code == 200
    token = entrada.json()["refresh_token"]
    for indice in range(2):
        ruim = client.post(
            "/auth/refresh",
            json={"refresh_token": f"lixo-{indice}-xxxx"},
        )
        assert ruim.status_code == 401
    bom = client.post("/auth/refresh", json={"refresh_token": token})
    assert bom.status_code == 200
    for indice in range(3):
        depois = client.post(
            "/auth/refresh",
            json={"refresh_token": f"depois-{indice}-xxxx"},
        )
        assert depois.status_code == 401
