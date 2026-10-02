# Migrations

- Nova mudança de tabela é um arquivo Alembic novo. 0001 a 0017 não são editados.
- Índice no Postgres nasce com `CREATE INDEX CONCURRENTLY`, fora de transação.
- O downgrade remove só o que a migration criou.
- O model e a migration vão no mesmo commit.
- O teste de drift compara o banco com os models. Ele só roda se `TEST_DATABASE_URL_PG` estiver definido.
- No CI o job sobe Postgres 16, roda `alembic upgrade head` e depois `pytest`.

Para experimentar no branch de staging do Neon, use a URL direta (sem `-pooler`) em `DATABASE_URL` e rode `alembic upgrade head`. Não rode isso no banco de produção sem um branch.
