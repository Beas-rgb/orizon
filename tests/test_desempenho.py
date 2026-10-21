"""Ciclo de avaliação de desempenho: criação, relações e cálculo."""

import json

import pytest
from sqlalchemy import select

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.desempenho import AvaliacaoRelacionamento
from tests.contas import SENHA_FUNC, abrir_consultora
from tests.test_orgao_acesso import _entrar_orgao


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
            "vinculo_titulo": "Desempenho",
        },
    )
    return headers, projeto.json()["id"]


def _funcionario(client, headers, projeto_id: str, email: str, nome: str) -> str:
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto_id,
            "email": email,
            "papel": "FUNCIONARIO",
            "nome": nome,
        },
    )
    corpo = next(
        item["corpo"]
        for item in reversed(caixa_email.mensagens)
        if item["destino"] == email
    )
    token = corpo.strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": SENHA_FUNC},
    )
    assert acesso.status_code == 200
    return acesso.json()["access_token"]


def _usuario_id(client, headers, projeto_id: str, email: str) -> str:
    equipe = client.get(f"/projetos/{projeto_id}/equipe", headers=headers).json()
    return next(item["id"] for item in equipe if item["email"] == email)


def test_ciclo_cria_com_escopo_e_pesos(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "escopo": "ORGANIZACAO",
            "configuracao": (
                '{"pesos": {"AUTO": 1, "SUPERIOR": 2, "SUBORDINADO": 1}, '
                '"ordem": ["AUTO", "SUPERIOR", "SUBORDINADO"]}'
            ),
        },
    )
    assert ciclo.status_code == 200
    dados = ciclo.json()
    assert dados["nome"] == "Avaliação 2026"
    assert dados["escopo"] == "ORGANIZACAO"
    assert dados["status"] == "RASCUNHO"


def test_ciclo_rejeita_config_com_codigo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "configuracao": '{"eval": "1+1"}',
        },
    )
    assert ciclo.status_code == 422


def test_gerar_relacoes_auto_superior_subordinado(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    gerente_email = "gerente@prefeitura.dev"
    _funcionario(client, headers, projeto_id, gerente_email, "Gerente")
    gerente_id = _usuario_id(client, headers, projeto_id, gerente_email)
    func_email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, func_email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, func_email)
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": func_id, "superior_id": gerente_id},
    )
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    gerar = client.post(
        f"/ciclos/{ciclo['id']}/gerar-relacoes",
        headers=headers,
    )
    assert gerar.status_code == 200
    assert gerar.json()["criados"] == 4  # AUTO, AUTO, SUPERIOR, SUBORDINADO

    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    assert len(relacoes) == 4
    tipos = {r.tipo_relacao for r in relacoes}
    assert tipos == {"AUTO", "SUPERIOR", "SUBORDINADO"}
    superior = next(r for r in relacoes if r.tipo_relacao == "SUPERIOR")
    assert superior.avaliador_id == gerente_id
    assert superior.avaliado_id == func_id


def test_gerar_relacoes_idempotente(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    primeiro = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    segundo = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    assert primeiro.json()["criados"] == 1
    assert segundo.json()["criados"] == 0
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    assert len(relacoes) == 1


def test_sem_superior_nao_cria_superior(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"],
            AvaliacaoRelacionamento.tipo_relacao == "SUPERIOR",
        )
    ).all()
    assert len(relacoes) == 0


def test_sem_subordinado_nao_cria_subordinado(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"],
            AvaliacaoRelacionamento.tipo_relacao == "SUBORDINADO",
        )
    ).all()
    assert len(relacoes) == 0


def _nota(client, token: str, relacao_id: str, pergunta_id: str, valor: int):
    return client.post(
        f"/relacionamentos/{relacao_id}/respostas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pergunta_id": pergunta_id, "valor_numerico": valor},
    )


def test_calcular_resultado_com_pesos(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    gerente_email = "gerente@prefeitura.dev"
    gerente_token = _funcionario(client, headers, projeto_id, gerente_email, "Gerente")
    gerente_id = _usuario_id(client, headers, projeto_id, gerente_email)
    func_email = "func@prefeitura.dev"
    func_token = _funcionario(client, headers, projeto_id, func_email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, func_email)
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": func_id, "superior_id": gerente_id},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    pergunta = client.post(
        f"/pesquisas/{pesquisa['id']}/perguntas",
        headers=headers,
        json={"texto": "Entrega", "tipo": "NOTA_5"},
    ).json()
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "configuracao": '{"pesos": {"AUTO": 1, "SUPERIOR": 2}}',
        },
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    auto = next(
        r for r in relacoes if r.tipo_relacao == "AUTO" and r.avaliado_id == func_id
    )
    superior = next(r for r in relacoes if r.tipo_relacao == "SUPERIOR")
    nota_auto = _nota(client, func_token, auto.id, pergunta["id"], 4)
    nota_superior = _nota(client, gerente_token, superior.id, pergunta["id"], 5)
    assert nota_auto.status_code == 200
    assert nota_superior.status_code == 200
    repetida = _nota(client, func_token, auto.id, pergunta["id"], 1)
    assert repetida.status_code == 409
    resultado = client.get(
        f"/ciclos/{ciclo['id']}/resultado/{func_id}",
        headers=headers,
    )
    assert resultado.status_code == 200
    dados = resultado.json()
    assert dados["resultado"] == 4.67  # (4*1 + 5*2) / 3
    assert dados["por_perspectiva"]["AUTO"] == 4.0
    assert dados["por_perspectiva"]["SUPERIOR"] == 5.0
    from app.models.desempenho import AvaliacaoResposta
    from app.models.pesquisa import Resposta

    assert db.scalar(select(AvaliacaoResposta).limit(1)) is not None
    assert db.scalar(select(Resposta).limit(1)) is None


def test_subordinado_sozinho_nao_aparece_para_a_chefia(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    chefe_token = _funcionario(client, headers, projeto_id, "chefe@p.dev", "Chefe")
    chefe_id = _usuario_id(client, headers, projeto_id, "chefe@p.dev")
    sub_token = _funcionario(client, headers, projeto_id, "sub@p.dev", "Sub")
    sub_id = _usuario_id(client, headers, projeto_id, "sub@p.dev")
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": sub_id, "superior_id": chefe_id},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho", "tipo": "DESEMPENHO"},
    ).json()
    pergunta = client.post(
        f"/pesquisas/{pesquisa['id']}/perguntas",
        headers=headers,
        json={"texto": "Entrega", "tipo": "NOTA_5"},
    ).json()
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Ciclo"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"],
            AvaliacaoRelacionamento.avaliado_id == chefe_id,
        )
    ).all()
    auto = next(r for r in relacoes if r.tipo_relacao == "AUTO")
    subordinado = next(r for r in relacoes if r.tipo_relacao == "SUBORDINADO")
    assert _nota(client, chefe_token, auto.id, pergunta["id"], 4).status_code == 200
    assert (
        _nota(client, sub_token, subordinado.id, pergunta["id"], 2).status_code
        == 200
    )
    caminho = f"/ciclos/{ciclo['id']}/resultado/{chefe_id}"

    da_chefia = client.get(
        caminho, headers={"Authorization": f"Bearer {chefe_token}"}
    ).json()
    assert "SUBORDINADO" not in da_chefia["por_perspectiva"]
    assert da_chefia["perspectivas_suprimidas"] == ["SUBORDINADO"]
    assert da_chefia["por_perspectiva"]["AUTO"] == 4.0

    da_consultora = client.get(caminho, headers=headers).json()
    assert da_consultora["por_perspectiva"]["SUBORDINADO"] == 2.0
    assert da_consultora["perspectivas_suprimidas"] == []


def test_resultado_404_fora_do_escopo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    func_token = _funcionario(client, headers, projeto_id, email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, email)
    outro_token = _funcionario(
        client, headers, projeto_id, "outro@prefeitura.dev", "Outro"
    )
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    caminho = f"/ciclos/{ciclo['id']}/resultado/{func_id}"
    assert client.get(caminho, headers=headers).status_code == 200
    propria = {"Authorization": f"Bearer {func_token}"}
    assert client.get(caminho, headers=propria).status_code == 200
    alheio = {"Authorization": f"Bearer {outro_token}"}
    assert client.get(caminho, headers=alheio).status_code == 404
    outra = abrir_consultora(client, email="outra@horizon.dev", nome="Outra")
    assert client.get(caminho, headers=outra).status_code == 404


def test_ciclo_atualiza_pesos_so_rascunho(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    ok = client.patch(
        f"/ciclos/{ciclo['id']}",
        headers=headers,
        json={
            "configuracao": (
                '{"pesos": {"AUTO": 1, "SUPERIOR": 3, "SUBORDINADO": 1}}'
            )
        },
    )
    assert ok.status_code == 200
    assert "SUPERIOR" in (ok.json()["configuracao"] or "")
    lista = client.get(f"/projetos/{projeto_id}/ciclos", headers=headers).json()
    assert lista[0]["id"] == ciclo["id"]
    assert lista[0]["configuracao"]


def test_relacao_lista_nomes(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "func@prefeitura.dev", "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = client.get(f"/ciclos/{ciclo['id']}/relacoes", headers=headers).json()
    assert relacoes[0]["avaliador_nome"] == "Funcionario"
    assert relacoes[0]["avaliado_nome"] == "Funcionario"


def test_relacao_nao_existente_404(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    outro = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Outro ciclo"},
    ).json()
    resp = client.get(
        f"/ciclos/{ciclo['id']}/relacao/{outro['id']}",
        headers=headers,
    )
    assert resp.status_code == 404


_PESOS = {"AUTO": 1, "SUPERIOR": 1, "SUBORDINADO": 3}


def recalcular(resposta: dict, pesos: dict) -> float:
    medias = resposta["por_perspectiva"]
    soma = sum(pesos[tipo] for tipo in medias)
    return sum(medias[tipo] * pesos[tipo] for tipo in medias) / soma


def _exato(resposta: dict, pesos: dict) -> None:
    assert resposta["resultado"] is not None
    assert round(resposta["resultado"], 2) == round(recalcular(resposta, pesos), 2)


def _nao_recupera(resposta: dict, pesos: dict, real: float) -> None:
    medias = resposta["por_perspectiva"]
    parcial = sum(medias[tipo] * pesos[tipo] for tipo in medias)
    soma = sum(pesos.values())
    achada = (resposta["resultado"] * soma - parcial) / pesos["SUBORDINADO"]
    assert round(achada, 2) != round(real, 2)


def _cena(
    client, monkeypatch, db, n_subs: int, pesos: dict, n_perguntas: int = 1
) -> dict:
    headers, projeto_id = _projeto(client, monkeypatch)

    def pessoa(email: str, nome: str, superior: str | None = None):
        token = _funcionario(client, headers, projeto_id, email, nome)
        uid = _usuario_id(client, headers, projeto_id, email)
        if superior:
            client.put(
                f"/projetos/{projeto_id}/perfis",
                headers=headers,
                json={"usuario_id": uid, "superior_id": superior},
            )
        return token, uid

    gerente, gerente_id = pessoa("gerente@p.dev", "Gerente")
    chefe, chefe_id = pessoa("chefe@p.dev", "Chefe", gerente_id)
    subs = [pessoa(f"sub{i}@p.dev", f"Sub {i}", chefe_id) for i in range(n_subs)]
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho", "tipo": "DESEMPENHO"},
    ).json()["id"]
    perguntas = []
    for indice in range(n_perguntas):
        criada = client.post(
            f"/pesquisas/{pesquisa}/perguntas",
            headers=headers,
            json={"texto": f"Entrega {indice}", "tipo": "NOTA_5"},
        ).json()["id"]
        perguntas.append(criada)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Ciclo", "configuracao": json.dumps({"pesos": pesos})},
    ).json()["id"]
    client.post(f"/ciclos/{ciclo}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo,
            AvaliacaoRelacionamento.avaliado_id == chefe_id,
        )
    ).all()
    return {
        "headers": headers,
        "chefe": chefe,
        "gerente": gerente,
        "subs": subs,
        "pergunta": perguntas[0],
        "perguntas": perguntas,
        "orgao": _entrar_orgao(client, "rh@prefeitura.dev"),
        "caminho": f"/ciclos/{ciclo}/resultado/{chefe_id}",
        "auto": next(r for r in relacoes if r.tipo_relacao == "AUTO"),
        "superior": next(r for r in relacoes if r.tipo_relacao == "SUPERIOR"),
        "por_sub": {
            r.avaliador_id: r for r in relacoes if r.tipo_relacao == "SUBORDINADO"
        },
    }


def _postar(client, token: str, relacao_id: str, pergunta_id: str, **corpo) -> None:
    resposta = client.post(
        f"/relacionamentos/{relacao_id}/respostas",
        headers={"Authorization": f"Bearer {token}"},
        json={"pergunta_id": pergunta_id, **corpo},
    )
    assert resposta.status_code == 200, resposta.text


def _responder(
    client, cena, auto, superior, numericas, textos=0, dupla=None
) -> None:
    pergunta = cena["pergunta"]
    fila = list(cena["subs"])
    if dupla:
        token, sub_id = fila.pop(0)
        relacao = cena["por_sub"][sub_id].id
        for valor, pergunta_id in zip(dupla, cena["perguntas"], strict=True):
            _postar(client, token, relacao, pergunta_id, valor_numerico=valor)
    envios = []
    if auto is not None:
        envios.append((cena["chefe"], cena["auto"].id, auto, None))
    if superior is not None:
        envios.append((cena["gerente"], cena["superior"].id, superior, None))
    for (token, sub_id), valor in zip(fila, numericas):
        envios.append((token, cena["por_sub"][sub_id].id, valor, None))
    resto = fila[len(numericas):]
    assert len(resto) == textos
    for token, sub_id in resto:
        envios.append((token, cena["por_sub"][sub_id].id, None, "sem nota"))
    for token, relacao, numero, texto in envios:
        corpo = {"valor_texto": texto} if texto else {"valor_numerico": numero}
        _postar(client, token, relacao, pergunta, **corpo)


def _vistas(client, cena) -> list[dict]:
    chefe = {"Authorization": f"Bearer {cena['chefe']}"}
    return [
        client.get(cena["caminho"], headers=chefe).json(),
        client.get(cena["caminho"], headers=cena["orgao"]).json(),
    ]


_CASOS = {
    "A": {"n": 1, "auto": 5, "sup": 5, "nums": [1], "nota": 5.0, "real": 1},
    "B": {"n": 4, "auto": 4, "sup": 5, "nums": [1, 2, 1, 2], "nota": 4.5, "real": 1.5},
    "C": {"n": 5, "auto": 4, "sup": 5, "nums": [3, 3, 3, 3, 3], "entra": True},
    "D": {"n": 1, "auto": 5, "sup": 5, "nums": [1], "nota": 5.0, "consultora": True},
    "E": {"n": 1, "auto": None, "sup": None, "nums": [1], "nulo": True},
    "F": {"n": 5, "auto": 4, "sup": 5, "nums": [2], "textos": 4},
    "F2": {
        "n": 5,
        "auto": 4,
        "sup": 5,
        "nums": [1, 2, 3, 4],
        "textos": 1,
        "nota": 4.5,
        "ve": True,
        "media_sub": 2.5,
        "nota_consultora": 3.3,
    },
    "F3": {
        "n": 5,
        "auto": 4,
        "sup": 5,
        "nums": [],
        "textos": 4,
        "dupla": [2, 4],
        "perguntas": 2,
        "nota": 4.5,
        "ve": True,
        "media_sub": 3.0,
        "nota_consultora": 3.6,
    },
}


@pytest.mark.parametrize("caso", ["A", "B", "C", "D", "E", "F", "F2", "F3"])
def test_nota_oculta_subordinado(client, monkeypatch, db, caso: str) -> None:
    item = _CASOS[caso]
    cena = _cena(
        client, monkeypatch, db, item["n"], _PESOS, item.get("perguntas", 1)
    )
    _responder(
        client,
        cena,
        item["auto"],
        item["sup"],
        item["nums"],
        item.get("textos", 0),
        item.get("dupla"),
    )
    if item.get("nulo"):
        assert cena["auto"].id and cena["superior"].id
        for vista in _vistas(client, cena):
            assert vista["resultado"] is None and vista["por_perspectiva"] == {}
        return
    if item.get("consultora"):
        dela = client.get(cena["caminho"], headers=cena["headers"]).json()
        assert dela["por_perspectiva"]["SUBORDINADO"] == 1.0
        assert dela["perspectivas_suprimidas"] == []
        _exato(dela, _PESOS)
    if item.get("ve"):
        dela = client.get(cena["caminho"], headers=cena["headers"]).json()
        assert dela["perspectivas_suprimidas"] == []
        assert round(dela["por_perspectiva"]["SUBORDINADO"], 2) == round(
            item["media_sub"], 2
        )
        assert round(dela["resultado"], 2) == round(item["nota_consultora"], 2)
        _exato(dela, _PESOS)
    for vista in _vistas(client, cena):
        oculto = not item.get("entra")
        assert (vista["perspectivas_suprimidas"] == ["SUBORDINADO"]) is oculto
        assert ("SUBORDINADO" not in vista["por_perspectiva"]) is oculto
        if "nota" in item:
            assert round(vista["resultado"], 2) == round(item["nota"], 2)
        _exato(vista, _PESOS)
        if "real" in item:
            _nao_recupera(vista, _PESOS, item["real"])
