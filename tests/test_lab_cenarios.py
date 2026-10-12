"""Criação de cenários sintéticos reprodutíveis."""

from sqlalchemy import create_engine, func, select

from app.core.config import settings
from app.main import incluir_lab_se_ligado
from app.models.base import Base
from app.models.usuario import Usuario
from app.services.lab.geradores import cnpj_sintetico, email_sintetico, montar_linhas
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA


def _headers(client, email: str) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": SENHA},
    )
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_mesma_seed_gera_mesmos_emails() -> None:
    a = montar_linhas(100, 42, "abcd1234-xxxx")
    b = montar_linhas(100, 42, "abcd1234-xxxx")
    assert [linha.email for linha in a] == [linha.email for linha in b]
    assert all(linha.email.endswith("@sintetico.invalid") for linha in a)
    assert email_sintetico(0, "abcd1234-xxxx") == a[0].email


def test_cnpj_sintetico_tem_digitos_validos() -> None:
    from app.services.lab.geradores import digito_cnpj

    numero = cnpj_sintetico(7, "cenario1")
    assert len(numero) == 14
    digitos = [int(c) for c in numero]
    assert digito_cnpj(
        digitos[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    ) == digitos[12]
    assert (
        digito_cnpj(digitos[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
        == digitos[13]
    )


def test_cria_cenario_100(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    monkeypatch.setattr(settings, "lab_max_participantes", 1000)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-cen@horizon.dev", SENHA)
    headers = _headers(client, "lab-cen@horizon.dev")
    criado = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Cem",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 99,
            "perfil": "NEUTRO",
        },
    )
    assert criado.status_code == 202, criado.text
    cid = criado.json()["id"]
    status = client.get(f"/lab/cenarios/{cid}", headers=headers)
    assert status.status_code == 200
    corpo = status.json()
    assert corpo["status"] == "PRONTO", corpo
    assert corpo["progresso"] == 100
    assert corpo["projeto_id"]

    qtd = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.email.like(f"%.{cid[:8]}@sintetico.invalid"))
    )
    assert qtd == 100
    tipos = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(
            Usuario.email.like(f"%.{cid[:8]}@sintetico.invalid"),
            Usuario.tipo_conta == "SINTETICO",
        )
    )
    assert tipos == 100


def test_tamanho_10_e_600_limites(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    monkeypatch.setattr(settings, "lab_max_participantes", 600)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-tam@horizon.dev", SENHA)
    headers = _headers(client, "lab-tam@horizon.dev")
    pequeno = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Dez",
            "tipo": "CLIMA",
            "tamanho": 10,
            "seed": 1,
            "perfil": "NEUTRO",
        },
    )
    assert pequeno.status_code == 202, pequeno.text
    cid = pequeno.json()["id"]
    qtd = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.email.like(f"%.{cid[:8]}@sintetico.invalid"))
    )
    assert qtd == 10
    recusa = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Grande",
            "tipo": "CLIMA",
            "tamanho": 5000,
            "seed": 2,
            "perfil": "NEUTRO",
        },
    )
    assert recusa.status_code == 422
    sem_staging = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Seiscentos",
            "tipo": "CLIMA",
            "tamanho": 600,
            "seed": 3,
            "perfil": "NEUTRO",
        },
    )
    assert sem_staging.status_code == 422


def test_volume_alto_fica_isolado(client, db, monkeypatch, tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'volume.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    monkeypatch.setattr(settings, "enable_lab", True)
    monkeypatch.setattr(settings, "lab_max_participantes", 1000)
    monkeypatch.setattr(settings, "staging_database_url", url)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-vol@horizon.dev", SENHA)
    headers = _headers(client, "lab-vol@horizon.dev")
    criado = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Volume",
            "tipo": "CLIMA",
            "tamanho": 250,
            "seed": 11,
            "perfil": "NEUTRO",
        },
    )
    assert criado.status_code == 202, criado.text
    cid = criado.json()["id"]
    corpo = client.get(f"/lab/cenarios/{cid}", headers=headers).json()
    assert corpo["status"] == "PRONTO", corpo
    assert corpo["projeto_id"] is None
    volume = create_engine(url)
    with volume.connect() as conexao:
        qtd = conexao.execute(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.email.like(f"%.{corpo['id'][:8]}@sintetico.invalid"))
        ).scalar()
    volume.dispose()
    assert qtd == 250
    no_principal = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.email.like(f"%.{corpo['id'][:8]}@sintetico.invalid"))
    )
    assert no_principal == 0
