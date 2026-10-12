"""Listagens com teto. Pedido acima do limite volta 422 antes do service."""

import pytest

from tests.contas import abrir_consultora


@pytest.mark.parametrize(
    "caminho",
    [
        "/biblioteca?limite=201",
        "/biblioteca?deslocamento=-1",
        "/projetos/qualquer/setores?limite=501",
        "/projetos/qualquer/cargos?limite=501",
    ],
)
def test_limite_acima_do_teto_e_recusado(client, caminho) -> None:
    headers = abrir_consultora(client)
    assert client.get(caminho, headers=headers).status_code == 422


def test_biblioteca_dentro_do_teto_responde(client) -> None:
    headers = abrir_consultora(client)
    resposta = client.get("/biblioteca?limite=200", headers=headers)
    assert resposta.status_code == 200
    assert resposta.json() == []
