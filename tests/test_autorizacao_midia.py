"""P0.5: mídia de rascunho só para consultora; órgão/funcionário → 404."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import SENHA_FUNC, SENHA_ORGAO, abrir_consultora

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
    )


def _entrar(client, destino: str, senha: str) -> dict[str, str]:
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_email(destino), "senha": senha},
    )
    assert acesso.status_code == 200
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def test_midia_rascunho_orgao_e_funcionario_404(client, monkeypatch):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto_id = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh-midia@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital midia",
        },
    ).json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    orgao = _entrar(client, "rh-midia@prefeitura.dev", SENHA_ORGAO)
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto_id,
            "email": "func-midia@orgao.dev",
            "papel": "FUNCIONARIO",
            "nome": "Func Midia",
        },
    )
    func = _entrar(client, "func-midia@orgao.dev", SENHA_FUNC)

    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Rascunho midia", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Com foto?", "tipo": "NOTA_5"},
    ).json()
    upload = client.post(
        f"/pesquisas/{pid}/perguntas/{pergunta['id']}/midia",
        headers=headers,
        files={"arquivo": ("a.png", PNG, "image/png")},
    )
    assert upload.status_code == 200

    caminho = f"/pesquisas/{pid}/perguntas/{pergunta['id']}/midia"
    assert client.get(caminho, headers=headers).status_code == 200
    assert client.get(caminho, headers=orgao).status_code == 404
    assert client.get(caminho, headers=func).status_code == 404
