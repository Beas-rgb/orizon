"""Concorrência: dois POST não podem duplicar resposta, publicação ou vínculo.

O TestClient não é um servidor de verdade. Os testes sequenciais cobrem a
regra de negócio (409/422). Os paralelos só garantem que não há 500 nem
linha duplicada no banco.
"""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.main import app
from app.models.desempenho import AvaliacaoRelacionamento
from app.models.estrutura import PerfilFuncionario
from app.models.usuario import Usuario
from app.services.estrutura import definir_perfil_funcionario
from app.services.pesquisa.desempenho import gerar_relacoes
from tests.contas import SENHA_FUNC, abrir_consultora


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
            "vinculo_titulo": "Concorrência",
        },
    )
    return headers, projeto.json()["id"]


def _funcionario(
    client, headers: dict[str, str], projeto_id: str, email: str, nome: str
) -> dict[str, str]:
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
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def _usuario_id(client, headers: dict[str, str], projeto_id: str, email: str) -> str:
    equipe = client.get(f"/projetos/{projeto_id}/equipe", headers=headers).json()
    return next(item["id"] for item in equipe if item["email"] == email)


def _publicar_clima(client, headers: dict[str, str], projeto_id: str) -> str:
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    ).json()
    client.post(
        f"/pesquisas/{pesquisa['id']}/perguntas",
        headers=headers,
        json={"texto": "Como avalia?", "tipo": "NOTA_5"},
    )
    return pesquisa["id"]


def _contar(modelo, **filtros) -> int:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        return len(db.scalars(select(modelo).filter_by(**filtros)).all())
    finally:
        db.close()


def test_resposta_segunda_vez_409(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    func = _funcionario(
        client, headers, projeto_id, "func@prefeitura.dev", "Funcionario"
    )
    pesquisa_id = _publicar_clima(client, headers, projeto_id)
    pub = client.post(f"/pesquisas/{pesquisa_id}/publicar", headers=headers)
    assert pub.status_code == 200
    pergunta_id = client.get(
        f"/eu/pesquisas/{pesquisa_id}/formulario", headers=func
    ).json()[0]["id"]
    corpo = {"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 3}]}
    primeiro = client.post(
        f"/eu/pesquisas/{pesquisa_id}/responder", headers=func, json=corpo
    )
    segundo = client.post(
        f"/eu/pesquisas/{pesquisa_id}/responder", headers=func, json=corpo
    )
    assert primeiro.status_code == 200
    assert segundo.status_code == 409


def test_publicar_segunda_vez_422(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    pesquisa_id = _publicar_clima(client, headers, projeto_id)
    primeiro = client.post(f"/pesquisas/{pesquisa_id}/publicar", headers=headers)
    segundo = client.post(f"/pesquisas/{pesquisa_id}/publicar", headers=headers)
    assert primeiro.status_code == 200
    assert segundo.status_code == 422


def test_gerar_relacoes_nao_duplica(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "func@prefeitura.dev", "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    primeiro = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    segundo = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    assert primeiro.status_code == 200
    assert segundo.status_code == 200
    assert _contar(AvaliacaoRelacionamento, ciclo_id=ciclo["id"]) == 1


def test_vinculo_duplo_nao_duplica_perfil(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "func@prefeitura.dev", "Funcionario")
    usuario_id = _usuario_id(client, headers, projeto_id, "func@prefeitura.dev")
    corpo = {"usuario_id": usuario_id}
    primeiro = client.put(f"/projetos/{projeto_id}/perfis", headers=headers, json=corpo)
    segundo = client.put(f"/projetos/{projeto_id}/perfis", headers=headers, json=corpo)
    assert primeiro.status_code == 200
    assert segundo.status_code == 200
    assert _contar(PerfilFuncionario, projeto_id=projeto_id, usuario_id=usuario_id) == 1


def _duas_sessoes(db):
    return sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)


def test_relacoes_duas_sessoes_nao_duplicam(client, monkeypatch, db) -> None:
    """Duas sessões no mesmo banco. A unique impede segunda linha."""
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "func@prefeitura.dev", "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    consultor_id = db.scalar(
        select(Usuario.id).where(Usuario.email == "tia@horizon.dev")
    )
    fabrica = _duas_sessoes(db)

    def gerar() -> None:
        sessao = fabrica()
        try:
            consultor = sessao.get(Usuario, consultor_id)
            gerar_relacoes(sessao, consultor, ciclo["id"])
        except Exception:
            sessao.rollback()
        finally:
            sessao.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: gerar(), range(2)))
    assert _contar(AvaliacaoRelacionamento, ciclo_id=ciclo["id"]) == 1


def test_vinculo_duas_sessoes_nao_duplica(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "func@prefeitura.dev", "Funcionario")
    usuario_id = _usuario_id(client, headers, projeto_id, "func@prefeitura.dev")
    consultor_id = db.scalar(
        select(Usuario.id).where(Usuario.email == "tia@horizon.dev")
    )
    fabrica = _duas_sessoes(db)

    def vincular() -> None:
        sessao = fabrica()
        try:
            consultor = sessao.get(Usuario, consultor_id)
            definir_perfil_funcionario(
                sessao, consultor, projeto_id, usuario_id
            )
        except Exception:
            sessao.rollback()
        finally:
            sessao.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: vincular(), range(2)))
    assert _contar(PerfilFuncionario, projeto_id=projeto_id, usuario_id=usuario_id) == 1
