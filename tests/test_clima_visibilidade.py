"""CLIMA: sem lista de nomes e sem painel ao vivo."""

import re

from app.models.projeto import Projeto
from tests.contas import SENHA_FUNC, abrir_consultora
from tests.test_anonimato_clima import _cnpj_falso, _entrar, _projeto_clima
from tests.test_orgao_acesso import _entrar_orgao


def _clima(client, monkeypatch, n: int):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client, email=f"tia{n}@horizon.dev", nome="Tia")
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": f"rh{n}@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Clima visivel",
        },
    )
    projeto_id = projeto.json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    acessos = []
    for indice in range(n):
        email = f"f{indice}-{n}@visivel.dev"
        client.post(
            "/auth/convites",
            headers=headers,
            json={
                "projeto_id": projeto_id,
                "email": email,
                "papel": "FUNCIONARIO",
                "nome": f"Func {indice}",
            },
        )
        acessos.append(_entrar(client, email, SENHA_FUNC))
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Nota?", "tipo": "NOTA_5"},
    ).json()["id"]
    publicado = client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    assert publicado.status_code == 200, publicado.text
    for acesso in acessos:
        envio = client.post(
            f"/eu/pesquisas/{pid}/responder",
            headers=acesso,
            json={"respostas": [{"pergunta_id": pergunta, "valor_numerico": 4}]},
        )
        assert envio.status_code == 200, envio.text
    return headers, projeto_id, pid, acessos


def _sem_numero(bloco: dict) -> None:
    assert bloco["suprimido"] is True
    assert bloco["respostas"] is None
    assert bloco["media"] is None


def test_painel_aberto_nao_mostra_numero(client, monkeypatch) -> None:
    headers, projeto_id, pid, _acessos = _clima(client, monkeypatch, 6)
    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers)
    assert painel.status_code == 200
    assert painel.json()
    for item in painel.json():
        _sem_numero(item)
    resumo = client.get(f"/projetos/{projeto_id}/resumo", headers=headers)
    assert resumo.status_code == 200
    perguntas = resumo.json()["pesquisas"][0]["perguntas"]
    assert all(item["media"] is None for item in perguntas)
    assert not re.search(r"\d{4}-\d{2}-\d{2}", painel.text)


def test_encerrada_respeita_piso(client, monkeypatch) -> None:
    headers, _projeto, pid, _acessos = _clima(client, monkeypatch, 5)
    encerrou = client.post(f"/pesquisas/{pid}/encerrar", headers=headers)
    assert encerrou.status_code == 200, encerrou.text
    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers).json()
    assert painel[0]["suprimido"] is False
    assert painel[0]["respostas"] == 5
    assert painel[0]["media"] == 4
    headers4, _p, pid4, _a = _clima(client, monkeypatch, 4)
    encerrou4 = client.post(f"/pesquisas/{pid4}/encerrar", headers=headers4)
    assert encerrou4.status_code == 200, encerrou4.text
    bloco = client.get(f"/pesquisas/{pid4}/painel", headers=headers4).json()[0]
    _sem_numero(bloco)


def test_orgao_ve_so_a_taxa(client, monkeypatch) -> None:
    headers, _projeto, pid, acessos = _clima(client, monkeypatch, 1)
    orgao = _entrar_orgao(client, "rh1@prefeitura.dev")
    dados = client.get(f"/pesquisas/{pid}/participantes", headers=orgao)
    assert dados.status_code == 200, dados.text
    corpo = dados.json()
    assert corpo["itens"] is None
    assert corpo["total"] == 1
    assert corpo["respondidas"] == 1
    assert "email" not in dados.text
    assert "@" not in dados.text
    consultora = client.get(f"/pesquisas/{pid}/participantes", headers=headers)
    assert consultora.json()["itens"] is None
    func = client.get(f"/pesquisas/{pid}/participantes", headers=acessos[0])
    assert func.status_code == 404
    outra = abrir_consultora(client, email="fora@horizon.dev", nome="Fora")
    alheio = client.get(f"/pesquisas/{pid}/participantes", headers=outra)
    assert alheio.status_code == 404
    assert client.get(f"/pesquisas/{pid}/painel", headers=outra).status_code == 404


def test_clima_encerrada_nao_reabre(client, monkeypatch, db) -> None:
    headers, _func, pid = _projeto_clima(
        client, monkeypatch, "reabre@visivel.dev"
    )
    assert client.post(f"/pesquisas/{pid}/encerrar", headers=headers).status_code == 200
    de_novo = client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    assert de_novo.status_code == 422
    client.patch(
        f"/pesquisas/{pid}",
        headers=headers,
        json={"titulo": "Ainda encerrada", "status": "PUBLICADA"},
    )
    from app.models.pesquisa import Pesquisa

    pesquisa = db.get(Pesquisa, pid)
    assert pesquisa is not None
    assert pesquisa.status == "ENCERRADA"
    projeto = db.get(Projeto, pesquisa.projeto_id)
    assert projeto is not None
    assert projeto.estado == "ABERTO"


def test_estado_do_projeto_nao_libera_resultado(client, monkeypatch) -> None:
    headers, projeto_id, pid, _acessos = _clima(client, monkeypatch, 5)
    mudou = client.patch(
        f"/projetos/{projeto_id}",
        headers=headers,
        json={"estado": "ENCERRADO"},
    )
    assert mudou.status_code == 200, mudou.text
    _sem_numero(client.get(f"/pesquisas/{pid}/painel", headers=headers).json()[0])
    encerrou = client.post(f"/pesquisas/{pid}/encerrar", headers=headers)
    assert encerrou.status_code == 200, encerrou.text
    aberto = client.patch(
        f"/projetos/{projeto_id}", headers=headers, json={"estado": "ABERTO"}
    )
    assert aberto.status_code == 200, aberto.text
    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers).json()[0]
    assert painel["suprimido"] is False
    assert painel["respostas"] == 5
