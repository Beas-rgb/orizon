# Desempenho

## Baseline do banco

Ainda não medido no Neon. O inventário de staging da Fase 0 não rodou.

## Latência e região

Regiões Render/Neon ainda não anotadas no painel (`docs/DEPLOY.md`).
`GET /health/db` devolve `latencia_ms` (SELECT 1 no processo). O número do Free
só vale depois de medir na URL de produção/staging — não inventar capacidade.

## Orçamento de consultas

Medido no SQLite dos testes, depois da Fase 2:

- `GET /auth/eu`: 1 consulta.
- `GET /projetos`: no máximo 6.
- `GET /projetos/{id}`: no máximo 7.

O login não segura a conexão do banco enquanto calcula o hash.

## Memória do hash

Estimativa do plano, não medida neste Free: 16 logins ao mesmo tempo, com 64 MiB cada, somavam cerca de 1.025 MiB. Agora o teto é 2 hashes ao mesmo tempo.

## Carga

Template da Fase 9. Preencher só após corrida em staging (`scripts/carga_staging.py`
ou Locust). Nenhum número abaixo é capacidade do Render nem do Neon até a data
da corrida.

| Campo | Valor |
|---|---|
| Data da corrida | |
| Ambiente (URL staging) | |
| Cenário | |
| Usuários / taxa | |
| p50 / p95 / erros | |
| CPU / RAM Render (painel) | |
| Conexões Neon (painel) | |
| Conclusão | _sem número de capacidade até fechar esta tabela_ |

## Banco desta fase

Os tempos de índice no Neon não foram medidos. O que os testes de SQLite cobrem é o comportamento: importação recusa a linha 5001, a árvore devolve filhos sob demanda e a limpeza apaga só a sessão vencida. O pool do processo passou a 5 conexões mais 5 de overflow, com espera de 10 segundos. Esgotar o pool responde 503 com `Retry-After: 3`.

## Resposta em rajada (Fase 4)

Medido no SQLite dos testes. Não é tempo de Render nem de Neon.

| | Antes (referência da fase, não recontada aqui) | Depois (teste desta máquina) |
|---|---|---|
| Comandos SQL, 1 pergunta | 31 | no máximo 20 (`tests/test_resposta_orcamento.py` passou) |
| Commits no sucesso | 2 | 1 |
| E-mails no request | 1 | 0 |
| Tempo no Neon | não medido | não medido |

O limite do envio conta só falha do usuário, não o IP e não o sucesso. Se o `commit` estoura, a API responde 503 e não deixa participante `RESPONDIDA` nem linha em `respostas`. O navegador reenvia até 5 vezes com espera aleatória. A prova de 100 usuários em 20 threads existe e foi pulada aqui: não há `TEST_DATABASE_URL_PG`. Ela roda no CI.

