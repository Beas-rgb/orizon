from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import abrir_consultora

SENHA = "Senha-segura1"


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def _projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital 12/2026",
        },
    )
    return headers, projeto.json()["id"]


def test_consultora_organiza_setor_e_config(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)

    setor = client.post(
        f"/projetos/{projeto_id}/setores",
        headers=headers,
        json={"nome": "Recursos Humanos"},
    )
    assert setor.status_code == 200
    lista = client.get(f"/projetos/{projeto_id}/setores", headers=headers)
    assert lista.json()[0]["nome"] == "Recursos Humanos"

    config = client.get(f"/projetos/{projeto_id}/configuracao", headers=headers)
    assert config.status_code == 200
    assert config.json()["ia_modo"] == "DESATIVADA"
    assert config.json()["pesquisas_habilitadas"] is False

    ligada = client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    assert ligada.json()["pesquisas_habilitadas"] is True
    assert ligada.json()["ia_modo"] == "DESATIVADA"


def test_orgao_nao_altera_nem_cria_setor(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "Senha-orgao1"},
    )
    orgao = {"Authorization": f"Bearer {acesso.json()['access_token']}"}

    negado = client.post(
        f"/projetos/{projeto_id}/setores",
        headers=orgao,
        json={"nome": "Educação"},
    )
    assert negado.status_code == 404

    patch = client.patch(
        f"/projetos/{projeto_id}",
        headers=orgao,
        json={"estado": "ENCERRADO"},
    )
    assert patch.status_code == 404

    leitura = client.get(f"/projetos/{projeto_id}/setores", headers=orgao)
    assert leitura.status_code == 200


def test_reenvio_cancela_token_antigo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    antigo = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    reenvio = client.post(
        f"/projetos/{projeto_id}/reenviar-convite",
        headers=headers,
    )
    assert reenvio.status_code == 200
    novo = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    assert novo != antigo

    velho = client.post(
        "/auth/primeiro-acesso",
        json={"token": antigo, "senha": "Senha-orgao1"},
    )
    assert velho.status_code == 400
    novo_acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": novo, "senha": "Senha-orgao1"},
    )
    assert novo_acesso.status_code == 200
