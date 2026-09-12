"""B6, B7, B8, B9: convite de órgão, CNPJ duplicado e onboarding."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import abrir_consultora


def _cnpj_qualquer(cnpj: str) -> DadosCnpj:
    digitos = "".join(ch for ch in cnpj if ch.isdigit()).zfill(14)[:14]
    return DadosCnpj(
        cnpj=digitos,
        razao_social=f"Orgao {digitos[-4:]}",
        nome_fantasia=f"Fantasia {digitos[-4:]}",
        municipio="Brasilia",
        uf="DF",
    )


def _rotulo_clima(client, headers):
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    return next(item for item in rotulos if item["codigo"] == "CLIMA")


def _criar(client, headers, rotulo_id, cnpj, email, titulo):
    return client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": rotulo_id,
            "cnpj": cnpj,
            "email_orgao": email,
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": titulo,
        },
    )


def test_cinco_projetos_seguidos_sem_429(client, monkeypatch) -> None:
    """B6: convite de órgão bem-sucedido não pode consumir o rate-limit."""
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_qualquer)
    headers = abrir_consultora(client)
    clima = _rotulo_clima(client, headers)
    status_codes = []
    for i in range(5):
        # CNPJs válidos sintéticos (14 dígitos distintos).
        base = f"19131243000{100 + i}"
        resp = _criar(
            client,
            headers,
            clima["id"],
            base,
            f"rh{i}@cliente.dev",
            f"Edital {i}",
        )
        status_codes.append(resp.status_code)
        assert resp.status_code == 200, resp.json()
        corpo = resp.json()
        assert corpo["convite_entrega"] == "ENVIADO"
        assert corpo["onboarding_estado"] == "convite_enviado"
        assert corpo["convite_motivo"] is None
    assert status_codes == [200, 200, 200, 200, 200]
    assert len(caixa_email.mensagens) >= 5


def test_cnpj_duplicado_mesma_consultora_409(client, monkeypatch) -> None:
    """B7 / T1: segundo projeto ativo com o mesmo CNPJ é bloqueado."""
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_qualquer)
    headers = abrir_consultora(client)
    clima = _rotulo_clima(client, headers)
    primeiro = _criar(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Edital 1",
    )
    assert primeiro.status_code == 200
    segundo = _criar(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "outro@prefeitura.dev",
        "Edital 2",
    )
    assert segundo.status_code == 409
    assert "CNPJ" in segundo.json()["detail"]


def test_email_orgao_ja_funcionario_traz_motivo(client, monkeypatch) -> None:
    """B9 / T4: NAO_ENVIADO com motivo quando o e-mail já é FUNCIONARIO."""
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_qualquer)
    headers = abrir_consultora(client)
    clima = _rotulo_clima(client, headers)
    base = _criar(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Projeto base",
    )
    assert base.status_code == 200
    projeto_id = base.json()["id"]
    convite_func = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Ana",
            "email": "ana@prefeitura.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": projeto_id,
        },
    )
    assert convite_func.status_code == 200
    token = next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == "ana@prefeitura.dev"
    )
    assert (
        client.post(
            "/auth/primeiro-acesso",
            json={"token": token, "senha": "Senha-func1"},
        ).status_code
        == 200
    )

    novo = _criar(
        client,
        headers,
        clima["id"],
        "00000000000191",
        "ana@prefeitura.dev",
        "Projeto com e-mail errado",
    )
    assert novo.status_code == 200
    corpo = novo.json()
    assert corpo["convite_entrega"] == "NAO_ENVIADO"
    assert corpo["onboarding_estado"] == "convite_pendente"
    assert corpo["convite_motivo"] == "email_ja_e_funcionario"
    assert corpo["email_orgao"] == "ana@prefeitura.dev"
