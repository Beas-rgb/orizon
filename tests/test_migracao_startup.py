"""Guardas de segurança para a leitura da revisão Alembic no boot."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core import migracao
from app.core.migracao import (
    MigracaoAdiada,
    _revisao_atual,
    aplicar,
    mapa_revisoes,
    origens_autorizadas,
)


def _url(tmp_path, nome: str = "schema.db") -> str:
    return f"sqlite:///{tmp_path / nome}"


def test_banco_vazio_pode_iniciar_a_cadeia_de_migracoes(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    engine.dispose()

    assert _revisao_atual(url) is None


def test_schema_existente_sem_alembic_version_nao_migra(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("CREATE TABLE usuarios (id TEXT PRIMARY KEY)"))
    engine.dispose()

    with pytest.raises(MigracaoAdiada, match="Nenhuma migration foi executada"):
        _revisao_atual(url)


def test_revisao_alembic_existente_e_retornada(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conexao.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0020_lab')")
        )
    engine.dispose()

    assert _revisao_atual(url) == "0020_lab"


def test_alembic_version_vazia_bloqueia_boot(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
    engine.dispose()

    with pytest.raises(RuntimeError, match="não contém uma revisão"):
        _revisao_atual(url)


def test_legado_deixa_a_api_subir_sem_upgrade(monkeypatch) -> None:
    from app.core import migracao

    def adiar(_url: str) -> str | None:
        raise MigracaoAdiada(
            "Migração adiada: teste. Nenhuma migration foi executada."
        )

    chamadas: list[str] = []
    monkeypatch.setattr(migracao, "_revisao_esperada", lambda: mapa_revisoes()[0])
    monkeypatch.setattr(migracao, "_revisao_atual", adiar)
    monkeypatch.setattr(migracao, "_upgrade", lambda _url: chamadas.append("up"))

    assert migracao.main() == 0
    assert chamadas == []


def test_erro_de_conexao_nao_e_convertido_em_ausencia_de_revisao(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'diretorio-inexistente' / 'schema.db'}"

    with pytest.raises(SQLAlchemyError):
        _revisao_atual(url)


def _proibir_alembic(monkeypatch) -> None:
    def proibido(*_args, **_kwargs):
        raise AssertionError("comando Alembic não deveria ser chamado")

    monkeypatch.setattr(migracao.command, "upgrade", proibido)
    monkeypatch.setattr(migracao.command, "stamp", proibido)


def _aplicar(atual: str | None, chamadas: list[str], **extras) -> str:
    head, conhecidas, ancestrais = mapa_revisoes()
    return aplicar(
        atual,
        head,
        "sqlite://",
        lambda: chamadas.append("up"),
        lambda: chamadas.append("lock"),
        conhecidas=conhecidas,
        ancestrais=ancestrais,
        **extras,
    )


def test_grafo_local_tem_um_head() -> None:
    head, conhecidas, ancestrais = mapa_revisoes()
    assert head == "0023_origem_sintetica"
    assert "0020_lab" in ancestrais
    assert "0021_indices_modelo" in ancestrais
    assert head in conhecidas and head not in ancestrais


def test_revisao_desconhecida_nao_chama_upgrade(monkeypatch) -> None:
    _proibir_alembic(monkeypatch)
    chamadas: list[str] = []
    with pytest.raises(RuntimeError, match="não existe no grafo"):
        _aplicar("revisao_inexistente", chamadas)
    assert chamadas == []


def test_revisao_anterior_sem_autorizacao_nao_atualiza(monkeypatch) -> None:
    _proibir_alembic(monkeypatch)
    chamadas: list[str] = []
    with pytest.raises(RuntimeError, match="MIGRACAO_ORIGENS_AUTORIZADAS"):
        _aplicar("0020_lab", chamadas, autorizadas=frozenset())
    assert chamadas == []


def test_revisao_anterior_autorizada_atualiza() -> None:
    chamadas: list[str] = []
    resultado = _aplicar("0020_lab", chamadas, autorizadas=frozenset({"0020_lab"}))
    assert resultado == "atualizada"
    assert chamadas == ["up"]


def test_origens_autorizadas_vem_da_configuracao() -> None:
    assert origens_autorizadas("") == frozenset()
    assert origens_autorizadas(" 0020_lab , ,0019_indice_superior") == frozenset(
        {"0020_lab", "0019_indice_superior"}
    )


def test_head_igual_nao_chama_upgrade_nem_stamp(monkeypatch) -> None:
    _proibir_alembic(monkeypatch)
    chamadas: list[str] = []
    head, _conhecidas, _ancestrais = mapa_revisoes()
    assert _aplicar(head, chamadas) == "migracoes em dia"
    assert chamadas == []


def _versao(tmp_path, valores: list[str]) -> str:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        for valor in valores:
            conexao.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": valor},
            )
    engine.dispose()
    return url


def test_mais_de_uma_revisao_bloqueia(tmp_path) -> None:
    url = _versao(tmp_path, ["0021_indices_modelo", "0020_lab"])
    with pytest.raises(RuntimeError, match="mais de uma revisão"):
        _revisao_atual(url)


def test_revisao_malformada_bloqueia(monkeypatch, tmp_path) -> None:
    _proibir_alembic(monkeypatch)
    url = _versao(tmp_path, ["0020 lab"])
    atual = _revisao_atual(url)
    chamadas: list[str] = []
    with pytest.raises(RuntimeError, match="malformada"):
        _aplicar(atual, chamadas)
    assert chamadas == []


def test_head_do_arquivo_divergente_bloqueia(monkeypatch) -> None:
    monkeypatch.setattr(migracao, "_revisao_esperada", lambda: "0020_lab")
    monkeypatch.setattr(
        migracao,
        "_revisao_atual",
        lambda _url: pytest.fail("não deveria ler o banco"),
    )
    with pytest.raises(RuntimeError, match="não coincide"):
        migracao.main()
