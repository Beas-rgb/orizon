"""EXPLAIN dos índices da 0021. Só PostgreSQL local descartável.

Recusa se TEST_DATABASE_URL_PG coincidir com DATABASE_URL da aplicação.
Não escreve. Não usa produção.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

INDICES = (
    "ix_convites_email",
    "ix_documentos_consultor_id",
    "ix_documentos_projeto_id",
    "ix_pedidos_consultora_email",
    "ix_projeto_usuarios_projeto_id",
    "ix_tokens_redefinicao_usuario_id",
)


def main() -> int:
    url = os.environ.get("TEST_DATABASE_URL_PG", "").strip()
    app = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("TEST_DATABASE_URL_PG ausente.")
        return 2
    if app and url == app:
        print("recusado: TEST_DATABASE_URL_PG igual a DATABASE_URL")
        return 2
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            if conexao.dialect.name != "postgresql":
                print("só PostgreSQL")
                return 2
            for nome in INDICES:
                plano = conexao.execute(
                    text("EXPLAIN SELECT 1 FROM pg_indexes WHERE indexname = :n"),
                    {"n": nome},
                ).all()
                print(nome)
                for linha in plano:
                    print(" ", linha[0])
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
