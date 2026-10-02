"""Guarda do laboratório: 404 e isolamento do TI."""

from fastapi import HTTPException

from app.core.config import settings
from app.core.lab import exigir_lab
from app.main import incluir_lab_se_ligado
from app.models.usuario import Usuario
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA, abrir_consultora


def _headers(client, email: str, senha: str = SENHA) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": senha},
    )
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_boot_com_lab_desligado_nao_monta() -> None:
    assert settings.enable_lab is False
    assert incluir_lab_se_ligado() is False


def test_consultora_normal_recebe_404_no_lab(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    assert incluir_lab_se_ligado() is True
    headers = abrir_consultora(client)
    assert client.get("/lab/cenarios", headers=headers).status_code == 404
    assert client.get("/lab/saude", headers=headers).status_code == 404


def test_consultor_teste_acessa_lab_e_nao_acessa_dev(
    client, db, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-guarda@horizon.dev", SENHA)
    headers = _headers(client, "lab-guarda@horizon.dev")
    assert client.get("/lab/saude", headers=headers).status_code == 200
    assert client.get("/lab/cenarios", headers=headers).status_code == 200
    assert client.get("/dev/pedidos", headers=headers).status_code == 404
    assert client.get("/dev/consultores", headers=headers).status_code == 404


def test_consultor_teste_usa_rotas_de_consultora(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    criar_consultor_teste(db, "Lab", "lab-ok@horizon.dev", SENHA)
    headers = _headers(client, "lab-ok@horizon.dev")
    assert client.get("/projetos", headers=headers).status_code == 200
    eu = client.get("/auth/eu", headers=headers)
    assert eu.status_code == 200
    assert eu.json()["tipo_conta"] == "TESTE"
    assert eu.json()["lab_habilitado"] is True


def test_lab_desligado_mesmo_com_rota_montada_da_404(
    client, db, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-off@horizon.dev", SENHA)
    headers = _headers(client, "lab-off@horizon.dev")
    monkeypatch.setattr(settings, "enable_lab", False)
    assert client.get("/lab/saude", headers=headers).status_code == 404


def test_exigir_lab_rejeita_ti(monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    ti = Usuario(
        nome="TI",
        email="ti-lab@horizon.dev",
        papel="TI",
        tipo_conta="NORMAL",
        ativo=True,
        tentativas_falhas=0,
    )
    try:
        exigir_lab(ti)
        raise AssertionError("deveria 404")
    except HTTPException as exc:
        assert exc.status_code == 404
