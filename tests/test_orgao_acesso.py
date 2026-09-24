"""Documento 01 — acesso permanente do órgão, avisos e multi-pesquisa."""

from sqlalchemy import func, select

from app.core.config import caminho_seguro_next, url_entrar_com_next
from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.notificacao import EntregaMensagem, Notificacao
from app.models.projeto import ProjetoUsuario
from app.models.usuario import Usuario
from app.services.identidade import (
    resolver_usuario_orgao_por_email,
    vincular_orgao_existente_ao_projeto,
)
from app.services.identidade.convites import (
    SIT_CONFLITO,
    SIT_NOVO,
    SIT_ORGAO_INATIVO,
)
from tests.contas import SENHA_ORGAO, abrir_consultora, abrir_dev


def _cnpj(cnpj: str) -> DadosCnpj:
    digitos = "".join(ch for ch in cnpj if ch.isdigit())
    if digitos == "00000000000191":
        return DadosCnpj(
            cnpj="00000000000191",
            razao_social="Camara Exemplo",
            nome_fantasia="Camara",
            municipio="Goiania",
            uf="GO",
        )
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def _rotulo_clima(client, headers) -> str:
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    return next(item for item in rotulos if item["codigo"] == "CLIMA")["id"]


def _criar_projeto(
    client,
    headers,
    *,
    cnpj: str,
    email: str,
    titulo: str,
    rotulo_id: str,
) -> dict:
    resp = client.post(
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
    assert resp.status_code == 200, resp.text
    return resp.json()


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
        and "primeiro acesso" in item["assunto"].lower()
        or (
            item["destino"] == destino
            and "senha" in item["assunto"].lower()
            and "criar" in item["assunto"].lower()
        )
        or (
            item["destino"] == destino
            and "?t=" in item["corpo"]
            and "primeiro" in item["corpo"].lower()
        )
    )


def _entrar_orgao(client, email: str) -> dict[str, str]:
    # Preferir mensagem de primeiro acesso (com token no final).
    corpo = next(
        item["corpo"]
        for item in reversed(caixa_email.mensagens)
        if item["destino"] == email
        and ("primeiro" in item["corpo"].lower() or "?t=" in item["corpo"])
    )
    token = corpo.strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": SENHA_ORGAO},
    )
    assert acesso.status_code == 200, acesso.text
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def test_caminho_seguro_next_bloqueia_open_redirect() -> None:
    assert caminho_seguro_next("/projetos/abc") == "/projetos/abc"
    assert caminho_seguro_next("/inicio") == "/inicio"
    assert caminho_seguro_next("https://evil.example") is None
    assert caminho_seguro_next("//evil.example") is None
    assert caminho_seguro_next("/admin") is None
    link = url_entrar_com_next("/projetos/x")
    assert "/entrar?next=" in link
    assert "projetos/x" in link


def test_email_novo_cria_convite_primeiro_acesso(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    antes = len(caixa_email.mensagens)
    projeto = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email="novo-orgao@prefeitura.dev",
        titulo="Edital novo",
        rotulo_id=rid,
    )
    assert projeto["id"]
    assert len(caixa_email.mensagens) > antes
    msg = caixa_email.mensagens[-1]
    assert msg["destino"] == "novo-orgao@prefeitura.dev"
    assert "senha" not in msg["assunto"].lower() or "criar" in msg["assunto"].lower()
    assert "?t=" in msg["corpo"]
    assert (
        "senha" not in msg["corpo"].lower()
        or "criada por você" in msg["corpo"].lower()
    )


def test_orgao_ativo_vincula_segundo_projeto_sem_novo_usuario(
    client, monkeypatch, db
) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "rh@prefeitura.dev"
    p1 = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Projeto 1",
        rotulo_id=rid,
    )
    orgao = _entrar_orgao(client, email)
    n_usuarios = db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.email == email)
    )
    assert n_usuarios == 1

    msgs_antes = len(caixa_email.mensagens)
    p2 = _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email=email,
        titulo="Projeto 2",
        rotulo_id=rid,
    )
    assert p2["id"] != p1["id"]
    n_depois = db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.email == email)
    )
    assert n_depois == 1

    # Sem segundo primeiro acesso: aviso de novo trabalho.
    novos = caixa_email.mensagens[msgs_antes:]
    assert any("novo trabalho" in m["assunto"].lower() for m in novos)
    assert not any(
        "?t=" in m["corpo"] and "primeiro" in m["corpo"].lower() for m in novos
    )

    lista = client.get("/projetos", headers=orgao).json()
    ids = {item["id"] for item in lista}
    assert p1["id"] in ids
    assert p2["id"] in ids

    vinculos = db.scalars(
        select(ProjetoUsuario).where(
            ProjetoUsuario.usuario_id
            == db.scalar(select(Usuario.id).where(Usuario.email == email))
        )
    ).all()
    assert len(vinculos) == 2


def test_vincular_orgao_idempotente(client, monkeypatch, db) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "idem@prefeitura.dev"
    projeto = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Idem",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    from app.models.projeto import Projeto

    proj = db.get(Projeto, projeto["id"])
    consultor = db.scalar(
        select(Usuario).where(Usuario.papel == "CONSULTOR")
    )
    assert usuario and proj and consultor
    assert vincular_orgao_existente_ao_projeto(db, consultor, proj, usuario) is False
    db.commit()
    n = db.scalar(
        select(func.count())
        .select_from(ProjetoUsuario)
        .where(
            ProjetoUsuario.projeto_id == projeto["id"],
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    assert n == 1


def test_funcionario_consultor_ti_nao_viram_orgao(client, monkeypatch, db) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    # Consultora já existe — usar e-mail dela no órgão.
    consultora = db.scalar(select(Usuario).where(Usuario.papel == "CONSULTOR"))
    assert consultora is not None
    resp = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": rid,
            "cnpj": "19131243000197",
            "email_orgao": consultora.email,
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Conflito consultor",
        },
    )
    assert resp.status_code == 200
    # Não vinculou como ORGAO.
    n = db.scalar(
        select(func.count())
        .select_from(ProjetoUsuario)
        .where(
            ProjetoUsuario.projeto_id == resp.json()["id"],
            ProjetoUsuario.papel == "ORGAO",
            ProjetoUsuario.usuario_id == consultora.id,
        )
    )
    assert n == 0
    resolucao = resolver_usuario_orgao_por_email(db, consultora.email)
    assert resolucao.situacao == SIT_CONFLITO

    abrir_dev(client)
    ti = db.scalar(select(Usuario).where(Usuario.papel == "TI"))
    assert ti is not None
    assert resolver_usuario_orgao_por_email(db, ti.email).situacao == SIT_CONFLITO


def test_orgao_inativo_nao_reativa(client, monkeypatch, db) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "inativo@prefeitura.dev"
    p1 = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Ativo",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    assert usuario is not None
    usuario.ativo = False
    db.commit()
    assert resolver_usuario_orgao_por_email(db, email).situacao == SIT_ORGAO_INATIVO

    p2 = _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email=email,
        titulo="Tenta reativar",
        rotulo_id=rid,
    )
    db.expire_all()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    assert usuario is not None
    assert usuario.ativo is False
    n = db.scalar(
        select(func.count())
        .select_from(ProjetoUsuario)
        .where(
            ProjetoUsuario.projeto_id == p2["id"],
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    assert n == 0
    assert p1["id"]


def test_aviso_novo_trabalho_sem_token_na_notificacao(
    client, monkeypatch, db
) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "aviso@prefeitura.dev"
    _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="P1",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email=email,
        titulo="P2",
        rotulo_id=rid,
    )
    avisos = db.scalars(
        select(Notificacao).where(Notificacao.tipo == "SISTEMA")
    ).all()
    assert avisos
    for aviso in avisos:
        baixo = aviso.mensagem.lower()
        assert "token" not in baixo
        assert "senha=" not in baixo
        assert "?t=" not in aviso.mensagem
    entregas = db.scalars(
        select(EntregaMensagem).where(
            EntregaMensagem.referencia == "AVISO_NOVO_TRABALHO"
        )
    ).all()
    assert entregas


def test_multiplas_pesquisas_mesmo_projeto(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "multi@prefeitura.dev"
    projeto = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Multi",
        rotulo_id=rid,
    )
    orgao = _entrar_orgao(client, email)
    pid = projeto["id"]
    client.patch(
        f"/projetos/{pid}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    a = client.post(
        f"/projetos/{pid}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2021", "tipo": "CLIMA"},
    )
    b = client.post(
        f"/projetos/{pid}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2023", "tipo": "CLIMA"},
    )
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["id"] != b.json()["id"]
    lista = client.get(f"/projetos/{pid}/pesquisas", headers=orgao).json()
    ids = {item["id"] for item in lista}
    assert a.json()["id"] in ids
    assert b.json()["id"] in ids
    # Antiga intacta
    assert a.json()["titulo"] == "Clima 2021"

    global_lista = client.get("/consultora/pesquisas", headers=headers)
    assert global_lista.status_code == 200
    gids = {item["id"] for item in global_lista.json()}
    assert a.json()["id"] in gids
    assert b.json()["id"] in gids

    # Órgão não vê listagem da consultora
    assert client.get("/consultora/pesquisas", headers=orgao).status_code == 404


def test_isolamento_orgao_nao_acessa_projeto_alheio(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    p_a = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email="a@prefeitura.dev",
        titulo="Projeto A",
        rotulo_id=rid,
    )
    p_b = _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email="b@camara.dev",
        titulo="Projeto B",
        rotulo_id=rid,
    )
    orgao_a = _entrar_orgao(client, "a@prefeitura.dev")
    assert client.get(f"/projetos/{p_b['id']}", headers=orgao_a).status_code == 404
    assert (
        client.get(f"/projetos/{p_b['id']}/pesquisas", headers=orgao_a).status_code
        == 404
    )
    assert p_a["id"]


def test_matriz_orgao_nao_abre_pesquisa_alheia(client, monkeypatch) -> None:
    """Órgão A conhece o id da pesquisa de B e mesmo assim recebe 404."""
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email="matriz-a@prefeitura.dev",
        titulo="Matriz A",
        rotulo_id=rid,
    )
    p_b = _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email="matriz-b@camara.dev",
        titulo="Matriz B",
        rotulo_id=rid,
    )
    client.patch(
        f"/projetos/{p_b['id']}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{p_b['id']}/pesquisas",
        headers=headers,
        json={"titulo": "Pesquisa B", "tipo": "CLIMA"},
    )
    assert pesquisa.status_code == 200
    orgao_a = _entrar_orgao(client, "matriz-a@prefeitura.dev")
    pid = pesquisa.json()["id"]
    assert client.get(f"/pesquisas/{pid}/perguntas", headers=orgao_a).status_code == 404
    assert client.get(f"/pesquisas/{pid}/painel", headers=orgao_a).status_code == 404
    assert (
        client.get(f"/projetos/{p_b['id']}/pesquisas", headers=orgao_a).status_code
        == 404
    )


def test_resolver_email_novo(db) -> None:
    r = resolver_usuario_orgao_por_email(db, "nunca-existiu@exemplo.dev")
    assert r.situacao == SIT_NOVO
    assert r.usuario is None


def test_publicar_envia_aviso_nova_pesquisa(client, monkeypatch, db) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "pub@prefeitura.dev"
    projeto = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Pub",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    pid = projeto["id"]
    client.patch(
        f"/projetos/{pid}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{pid}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    client.post(
        f"/pesquisas/{pesquisa['id']}/perguntas",
        headers=headers,
        json={"texto": "Como avalia?", "tipo": "NOTA_5"},
    )
    msgs_antes = len(caixa_email.mensagens)
    pub = client.post(f"/pesquisas/{pesquisa['id']}/publicar", headers=headers)
    assert pub.status_code == 200
    db.expire_all()
    avisos = db.scalars(
        select(Notificacao).where(
            Notificacao.tipo == "PESQUISA",
            Notificacao.titulo.contains("nova pesquisa"),
        )
    ).all()
    assert avisos
    assert all("?t=" not in a.mensagem for a in avisos)
    entregas = db.scalars(
        select(EntregaMensagem).where(
            EntregaMensagem.referencia == "AVISO_NOVA_PESQUISA"
        )
    ).all()
    assert entregas
    assert all(item.status == "ENVIADO" for item in entregas)
    novos = caixa_email.mensagens[msgs_antes:]
    assert any("nova pesquisa" in m["assunto"].lower() for m in novos)
    assert all("?t=" not in m["corpo"] for m in novos)
