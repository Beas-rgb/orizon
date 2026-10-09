# Migrations

> Nota 08/10/2026: no git o head é `0020_lab` (`migrations/versions/`). Isso não prova a revisão do Neon. Não aplicar `alembic stamp` nem `alembic upgrade` no destino do Render até o P0 em `docs/RELATORIO_PASSO_0_2026-10-08.md`. Staging só com restore combinado e URL direta. Estado vivo: `docs/INDEX_PLANO_MESTRE_50K.md`.

- Nova mudança de tabela é um arquivo Alembic novo. 0001 a 0017 não são editados.
- Índice no Postgres nasce com `CREATE INDEX CONCURRENTLY`, fora de transação.
- O downgrade remove só o que a migration criou.
- O model e a migration vão no mesmo commit.
- O teste de drift compara o banco com os models. Ele só roda se `TEST_DATABASE_URL_PG` estiver definido.
- No CI o job sobe Postgres 16, roda `alembic upgrade head` e depois `pytest`.

Para experimentar no branch de staging do Neon, use a URL direta (sem `-pooler`) em `DATABASE_URL` e rode `alembic upgrade head`. Não rode isso no banco de produção sem um branch.
