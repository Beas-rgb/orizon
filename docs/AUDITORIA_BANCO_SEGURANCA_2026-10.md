# Auditoria de banco e segurança — 08/10/2026

**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Escopo desta nota:** leitura do git e dos docs. Sem pytest, sem SQL no Neon, sem painel do Render.

Cada linha diz o estado da evidência. “Verificado” aqui significa arquivo lido, não bug reproduzido nem correção provada.

## Banco

| Item | Estado | Nota |
|---|---|---|
| Head Alembic no git é `0020_lab` | Verificado no snapshot | 20 arquivos em `migrations/versions/`. Não consulta `alembic_version` no Neon. |
| Docs ainda citam teto 0017–0019 | Verificado no snapshot | `docs/MIGRATIONS.md` e `docs/DATA_MODEL.md` estavam atrás do git. Nota de 08/10 aponta isso. Não é drift medido no banco. |
| 21 tabelas no contexto mestre | Relatado | Dump antigo em `docs/HORIZON_CONTEXTO_IA.md`. Não recontado. |
| 22 tabelas no Neon | Relatado | Capa da revisão 1.1. O dossiê não veio no patch. Não está comprovado que é o banco do Render. |
| `DATABASE_URL` do Render = projeto Neon anotado em 02/10 | Pendente | P0. Conferir na tela. Não colar a URL. |
| `alembic stamp` / `upgrade` / `scripts/reset_manter_ti.py` | Pendente, proibido até o P0 | O script existe. Não foi executado. |

Diferença coluna a coluna entre models e o banco **não foi produzida**. Inventar essa lista quebraria o Passo 0.

## Segurança

| Item | Estado | Nota |
|---|---|---|
| Isolamento IDOR → 404 descrito no RC | Relatado | `docs/RELEASE_CANDIDATE.md` cita `tests/test_matriz_seguranca_rc.py`. O arquivo existe. A suíte não rodou em 08/10. |
| Anonimato de CLIMA | Relatado, em conflito entre docs | Setembro: elo resposta → token → usuário ainda utilizável para identificar. Diário posterior: elo cortado e K=5. Sem reexecução, os dois ficam abertos. |
| `tests/test_anonimato_clima.py` | Verificado no snapshot | Arquivo presente. Resultado de 08/10: não executado. |
| Sessão (Argon2id, fila de hash, refresh, hops 0) | Relatado no doc vivo | `docs/SECURITY.md`. Não retestado neste Passo 0. |
| CI (pytest + Alembic no Postgres 16) | Verificado no snapshot | `.github/workflows/ci.yml` existe. Não foi disparado aqui. |
| Segredos neste PR | Verificado no snapshot | Este documento não contém connection string, senha nem token. |

## Testes de aceite (ainda não rodados)

Quando o P0 do banco fechar e houver staging com restore:

- `alembic upgrade head` só no staging, com a URL direta, depois de confirmar que não é produção.
- `pytest` com o job de CI (ou o mesmo comando local), e o número de passed/failed anotado na data.
- Cruzar organização: recurso de A pedido por B devolve 404.
- CLIMA: agregado some abaixo de K=5; a resposta não volta com o nome do autor.
- Nenhum desses itens está marcado como passou em 08/10.
