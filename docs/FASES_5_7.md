# Fases 5–7 — testes, capacidade e piloto

Estas fases **não rodaram contra produção**. Números de capacidade são metas, não prova. Staging pago e branch Neon isolado continuam pendência humana.

## Fase 5 — testes, integração e observabilidade

- Suítes PostgreSQL locais: `TEST_DATABASE_URL_PG` no container `horizon-pg-ensaio:54329`. A suíte recusa a URL se ela coincidir com `DATABASE_URL` da aplicação. SQLite não vale como evidência de Postgres.
- Já existem no repositório: `tests/test_schema_drift.py`, `tests/test_timeouts_pg.py`, `tests/test_resposta_concorrente_pg.py`.
- E2E no navegador: só contra staging com dados sintéticos. Sem staging isolado, o gate fica aberto.
- Logs: `LogAcesso` grava `request_id`, método, caminho mascarado, status e ms. Sem corpo, token ou e-mail.
- Métricas de pool, latência e jobs: `/health/db` devolve `latencia_ms`; `/health/ready` não escreve; tarefas longas em `GET /tarefas`.

## Fase 6 — capacidade (metas S0–S9)

Até existir relatório de p50/p95/p99, RPS, taxa de erro, pool e integridade, **não afirmar** que o sistema aguenta N usuários.

| Cenário | Meta (não medida) |
|---|---|
| S0 | fumaça 10 usuários |
| S1 | 50 |
| S2 | 100 |
| S3 | 250 |
| S4 | 500 |
| S5 | rampa 10→500 |
| S6 | 5 mil respostas com a semântica K=5 |
| S7 | concorrência de envio (já há teste PG de duas submissões) |
| S8 | importação em lote no limite `IMPORT_MAX_LINHAS` |
| S9 | laboratório 600 sintéticos na base isolada (`STAGING_DATABASE_URL`) |

Corrida só em staging equivalente ao plano pago. Produção: nenhuma escrita.

## Fase 7 — piloto real (critérios da seção 15 do brief)

Checklist humano, nenhum item marcado como feito daqui:

- [ ] Destino do banco Render/Neon conferido no painel (sem colar segredo)
- [ ] Backup e restore/PITR comprovados
- [ ] R2 e e-mail verificados
- [ ] LGPD aprovada
- [ ] Procedimento de incidente e rollback escrito
- [ ] Schema na revisão do head (`/health/ready` 200)
- [ ] Laboratório desligado (`ENABLE_LAB` recusado em produção)

Motor analítico de IA e PWA ficam fora desta execução.
