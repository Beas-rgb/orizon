"""Exclusão completa e verificada de cenários."""

from sqlalchemy import func, select

from app.core.config import settings
from app.main import incluir_lab_se_ligado
from app.models.lab import CenarioLab
from app.models.organizacao import Organizacao
from app.models.projeto import Projeto
from app.models.usuario import Usuario
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA, abrir_consultora


def _headers(client, email: str) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": SENHA},
    )
    assert entrada.status_code == 200
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_exclui_cenario_sem_residuos(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-exc@horizon.dev", SENHA)
    headers = _headers(client, "lab-exc@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Apagar",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 3,
            "perfil": "ALEATORIO",
        },
    ).json()["id"]
    cenario = db.get(CenarioLab, cid)
    assert cenario and cenario.projeto_id
    projeto_id = cenario.projeto_id
    projeto = db.get(Projeto, projeto_id)
    assert projeto is not None
    org_id = projeto.organizacao_id

    normal = db.scalar(
        select(func.count()).select_from(Usuario).where(
            Usuario.tipo_conta == "TESTE"
        )
    )

    errado = client.delete(
        f"/lab/cenarios/{cid}",
        headers=headers,
        params={"confirmo": "nome-errado"},
    )
    assert errado.status_code == 422

    ok = client.delete(
        f"/lab/cenarios/{cid}",
        headers=headers,
        params={"confirmo": "Apagar"},
    )
    assert ok.status_code == 202, ok.text
    db.expire_all()
    resto = db.get(CenarioLab, cid)
    assert resto is None, getattr(resto, "erro", None) or getattr(resto, "status", None)
    assert db.get(Projeto, projeto_id) is None
    assert db.get(Organizacao, org_id) is None
    restam = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.email.like(f"%.{cid[:8]}@sintetico.invalid"))
    )
    assert restam == 0
    ainda_teste = db.scalar(
        select(func.count()).select_from(Usuario).where(
            Usuario.tipo_conta == "TESTE"
        )
    )
    assert ainda_teste == normal


def test_outro_dono_nao_apaga(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-a@horizon.dev", SENHA)
    criar_consultor_teste(db, "Lab", "lab-b@horizon.dev", SENHA)
    ha = _headers(client, "lab-a@horizon.dev")
    hb = _headers(client, "lab-b@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=ha,
        json={
            "nome": "Privado",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 4,
            "perfil": "ALEATORIO",
        },
    ).json()["id"]
    assert (
        client.delete(
            f"/lab/cenarios/{cid}",
            headers=hb,
            params={"confirmo": "Privado"},
        ).status_code
        == 404
    )


def test_consultora_normal_nao_ve_projeto_lab(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    normal = abrir_consultora(client)
    criar_consultor_teste(db, "Lab", "lab-iso@horizon.dev", SENHA)
    headers = _headers(client, "lab-iso@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Iso",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 5,
            "perfil": "ALEATORIO",
        },
    ).json()["id"]
    projeto_id = client.get(f"/lab/cenarios/{cid}", headers=headers).json()[
        "projeto_id"
    ]
    assert client.get(f"/projetos/{projeto_id}", headers=normal).status_code == 404
