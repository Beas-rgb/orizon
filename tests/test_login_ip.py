"""30 senhas erradas no mesmo IP esperam. Outro IP não entra na conta."""

from app.core.config import settings


def test_limite_de_ip_no_login(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_ip_max_falhas", 3)
    monkeypatch.setattr(
        "app.services.identidade.auth.senha_confere",
        lambda *_args, **_kwargs: False,
    )
    for indice in range(2):
        resposta = client.post(
            "/auth/login",
            json={"email": f"pessoa{indice}@horizon.dev", "senha": "Errada-1!"},
        )
        assert resposta.status_code == 401
    terceira = client.post(
        "/auth/login",
        json={"email": "pessoa9@horizon.dev", "senha": "Errada-1!"},
    )
    assert terceira.status_code == 429


def test_outro_ip_nao_herda_o_bloqueio(db, monkeypatch) -> None:
    from app.services.identidade.auth import login
    from app.services.identidade.erros import ErroAuth

    monkeypatch.setattr(settings, "login_ip_max_falhas", 2)
    monkeypatch.setattr(
        "app.services.identidade.auth.senha_confere",
        lambda *_args, **_kwargs: False,
    )
    primeira = None
    try:
        login(db, "a@horizon.dev", "Errada-1!", ip="10.0.0.1")
    except ErroAuth as exc:
        primeira = exc.status
    assert primeira == 401
    try:
        login(db, "a2@horizon.dev", "Errada-1!", ip="10.0.0.1")
        raise AssertionError("deveria bloquear")
    except ErroAuth as exc:
        assert exc.status == 429
    try:
        login(db, "b@horizon.dev", "Errada-1!", ip="10.0.0.2")
        raise AssertionError("deveria negar a senha")
    except ErroAuth as exc:
        assert exc.status == 401
