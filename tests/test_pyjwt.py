"""PyJWT aceita o token antigo do python-jose e rejeita token adulterado."""

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.tokens import criar_access_token, ler_access_token

SEGREDO = "x" * 32
TOKEN_JOSE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJ1MSIsInBhcGVsIjoiVEkiLCJ0eXAiOiJhY2Nlc3MiLCJzaWQiOiJzMSIsImV4cCI6NDEwMjQ0NDgwMH0."
    "YdUH4X-QAEOotLVZzTjTuHdjl8cRQYy850AdSRxJCbA"
)


def test_token_jose_antigo_continua_valido(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", SEGREDO)
    dados = ler_access_token(TOKEN_JOSE)
    assert dados["sub"] == "u1"
    assert dados["sid"] == "s1"


def test_ida_e_volta(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", SEGREDO)
    token = criar_access_token("u2", "CONSULTOR", sessao_id="s2")
    assert ler_access_token(token)["sid"] == "s2"


def test_expirado_segredo_errado_e_adulterado(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", SEGREDO)
    vencido = jwt.encode(
        {
            "sub": "u1",
            "papel": "TI",
            "typ": "access",
            "sid": "s1",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        SEGREDO,
        algorithm="HS256",
    )
    try:
        ler_access_token(vencido)
        raise AssertionError("expirado")
    except ValueError:
        pass
    monkeypatch.setattr(settings, "jwt_secret", "y" * 32)
    try:
        ler_access_token(TOKEN_JOSE)
        raise AssertionError("segredo")
    except ValueError:
        pass
    monkeypatch.setattr(settings, "jwt_secret", SEGREDO)
    partes = TOKEN_JOSE.split(".")
    adulterado = partes[0] + "." + partes[1] + ".aaaa"
    try:
        ler_access_token(adulterado)
        raise AssertionError("adulterado")
    except ValueError:
        pass


def test_alg_none_rejeitado(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", SEGREDO)
    falso = jwt.encode(
        {"sub": "u1", "typ": "access", "sid": "s1", "exp": 4102444800},
        "",
        algorithm="none",
    )
    try:
        ler_access_token(falso)
        raise AssertionError("none")
    except ValueError:
        pass
