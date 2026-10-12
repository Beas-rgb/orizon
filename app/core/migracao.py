"""Sobe a revisão só quando a origem é conhecida e autorizada.

`python -m app.core.migracao`.
"""

import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings

TRAVA = 727274
REVISAO_VALIDA = re.compile(r"[A-Za-z0-9_]+")


class MigracaoAdiada(RuntimeError):
    """O schema legado permanece. A API sobe e nenhuma migration roda."""


def origens_autorizadas(valor: str | None = None) -> frozenset[str]:
    """Revisões anteriores ao head que o boot pode atualizar sozinho."""
    bruto = settings.migracao_origens_autorizadas if valor is None else valor
    return frozenset(item.strip() for item in bruto.split(",") if item.strip())


def mapa_revisoes() -> tuple[str, set[str], set[str]]:
    """Lê o grafo local de migrations. Não conecta no banco."""
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(
            "Migração automática bloqueada: o grafo local não tem um único head."
        )
    head = heads[0]
    conhecidas = {revisao.revision for revisao in script.walk_revisions()}
    ancestrais = {
        revisao.revision
        for revisao in script.iterate_revisions(head, None)
        if revisao.revision != head
    }
    return head, conhecidas, ancestrais


def decidir(
    atual: str | None,
    esperada: str,
    conhecidas: set[str],
    ancestrais: set[str],
    autorizadas: frozenset[str],
) -> str:
    """Retorna instalar, em_dia ou atualizar. Qualquer outro estado é erro."""
    if esperada not in conhecidas:
        raise RuntimeError(
            "Migração automática bloqueada: ALEMBIC_HEAD não pertence ao grafo "
            "local. Nenhuma alteração foi feita."
        )
    if atual is None:
        return "instalar"
    if not REVISAO_VALIDA.fullmatch(atual):
        raise RuntimeError(
            "Migração automática bloqueada: a revisão registrada é malformada. "
            "Nenhuma alteração foi feita."
        )
    if atual == esperada:
        return "em_dia"
    if atual not in conhecidas:
        raise RuntimeError(
            "Migração automática bloqueada: a revisão registrada não existe no "
            "grafo local. Nenhuma alteração foi feita."
        )
    if atual not in ancestrais:
        raise RuntimeError(
            "Migração automática bloqueada: a revisão registrada não é anterior "
            "ao head. Nenhuma alteração foi feita."
        )
    if atual not in autorizadas:
        raise RuntimeError(
            "Migração automática bloqueada: a revisão registrada é anterior ao "
            "head e não está em MIGRACAO_ORIGENS_AUTORIZADAS. "
            "Nenhuma alteração foi feita."
        )
    return "atualizar"


def url_direta(database_url: str, direta: str = "") -> str:
    """Prefere a URL direta. Tira `-pooler` do host quando ela não vier pronta."""
    if direta.strip():
        return direta.strip()
    return database_url.replace("-pooler", "", 1)


def eh_postgres(url: str) -> bool:
    return url.startswith("postgres")


def aplicar(
    atual: str | None,
    esperada: str,
    url: str,
    upgrade,
    travar,
    *,
    conhecidas: set[str] | None = None,
    ancestrais: set[str] | None = None,
    autorizadas: frozenset[str] | None = None,
) -> str:
    """Igual: não migra. Postgres trava antes. SQLite não usa advisory lock."""
    if conhecidas is None or ancestrais is None:
        _head, conhecidas, ancestrais = mapa_revisoes()
    acao = decidir(
        atual,
        esperada,
        conhecidas,
        ancestrais,
        origens_autorizadas() if autorizadas is None else autorizadas,
    )
    if acao == "em_dia":
        return "migracoes em dia"
    if eh_postgres(url):
        travar()
    upgrade()
    return "atualizada"


def _revisao_esperada() -> str:
    candidatos = [
        Path("/app/ALEMBIC_HEAD"),
        Path(__file__).resolve().parents[2] / "ALEMBIC_HEAD",
    ]
    for caminho in candidatos:
        if caminho.is_file():
            return caminho.read_text(encoding="utf-8").strip().split()[0]
    raise SystemExit("ALEMBIC_HEAD ausente. O build da imagem deve gerá-lo.")


def _revisao_atual(url: str) -> str | None:
    """Lê a revisão sem confundir erro de conexão com banco sem versão.

    Um schema não vazio sem `alembic_version` é ambíguo: pode ser legado ou
    resultado de uma instalação parcialmente concluída. Nesse caso, não inicia
    uma cadeia histórica de migrations automaticamente.
    """
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            insp = inspect(conexao)
            schema = "public" if conexao.dialect.name == "postgresql" else None
            tabelas = set(insp.get_table_names(schema=schema))

            if "alembic_version" not in tabelas:
                vistas = set(insp.get_view_names(schema=schema))
                objetos = sorted(tabelas | vistas)
                if objetos:
                    amostra = ", ".join(objetos[:8])
                    sufixo = ", ..." if len(objetos) > 8 else ""
                    raise MigracaoAdiada(
                        "Migração adiada: o banco contém objetos "
                        f"({amostra}{sufixo}), mas não possui alembic_version. "
                        "Nenhuma migration foi executada. "
                        "A API segue com o schema atual."
                    )
                return None

            linhas = (
                conexao.execute(text("select version_num from alembic_version"))
                .scalars()
                .all()
            )
            if len(linhas) > 1:
                raise RuntimeError(
                    "Migração automática bloqueada: alembic_version contém mais "
                    "de uma revisão. Nenhuma alteração foi feita."
                )
            atual = linhas[0] if linhas else None
            if atual is None or not str(atual).strip():
                raise RuntimeError(
                    "Migração automática bloqueada: alembic_version existe, mas "
                    "não contém uma revisão. Verifique o estado do banco antes "
                    "de executar migrations."
                )
            return str(atual)
    finally:
        engine.dispose()


def _travar(url: str):
    engine = create_engine(url)
    conexao = engine.connect()
    conexao.execute(text(f"SELECT pg_advisory_lock({TRAVA})"))
    conexao.commit()
    return conexao


def _soltar(conexao) -> None:
    conexao.execute(text(f"SELECT pg_advisory_unlock({TRAVA})"))
    conexao.commit()
    conexao.close()


def _upgrade(url: str) -> None:
    anterior = settings.database_url
    settings.database_url = url
    try:
        comando = Config("alembic.ini")
        command.upgrade(comando, "head")
    finally:
        settings.database_url = anterior


def main() -> int:
    esperada = _revisao_esperada()
    head, conhecidas, ancestrais = mapa_revisoes()
    if esperada != head:
        raise RuntimeError(
            "Migração automática bloqueada: ALEMBIC_HEAD não coincide com o head "
            "do grafo local."
        )
    url = url_direta(settings.database_url, settings.database_url_direct)
    try:
        atual = _revisao_atual(url)
    except MigracaoAdiada as exc:
        print(exc)
        return 0
    trava = None

    def travar() -> None:
        nonlocal trava
        trava = _travar(url)

    try:
        resultado = aplicar(
            atual,
            esperada,
            url,
            lambda: _upgrade(url),
            travar,
            conhecidas=conhecidas,
            ancestrais=ancestrais,
        )
    finally:
        if trava is not None:
            _soltar(trava)
    print(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
