# Carga no staging — boot RC

Medição progressiva `10 → 20 → 50 → 100 → 200 → 300` contra `/health`.
O script **recusa** URL de produção (`orizon-api.onrender.com` e afins).

## Como rodar

```bash
# Local (API já no ar)
python scripts/carga_staging.py --local

# Staging (URL precisa ter "staging" no host)
HORIZON_AMBIENTE=staging \
HORIZON_CARGA_URL=https://orizon-staging.exemplo/health \
python scripts/carga_staging.py
```

## O que mede

| Campo | Significado |
|---|---|
| n | requisições simultâneas do passo |
| p50 / p95 / p99 | latência em ms |
| erro % | respostas falhas |
| rps | requisições por segundo |

CPU/RAM e conexões do banco saem do painel do Render/Neon no momento da corrida.
Não grava esses números no repositório (variam por máquina).

## Aceite do passo

- erro % = 0 no `/health` até 100 concorrentes
- p95 sobe de forma previsível; sem 5xx
- depois de 200–300, anotar se o plano free do Render satura

Harness local comprovado em `tests/test_carga_harness.py`.

## Medição local (TestClient `/health`, 25/09/2026)

| n | ok | erro % | rps | p50 ms | p95 ms | p99 ms |
|---|---|---|---|---|---|---|
| 10 | 10 | 0 | 99 | 3.3 | 69.7 | 69.7 |
| 20 | 20 | 0 | 196 | 2.8 | 3.3 | 48.3 |
| 50 | 50 | 0 | 353 | 2.8 | 3.4 | 3.6 |
| 100 | 100 | 0 | 335 | 3.0 | 3.5 | 3.8 |
| 200 | 200 | 0 | 349 | 2.8 | 3.3 | 3.6 |
| 300 | 300 | 0 | 315 | 3.1 | 4.0 | 4.6 |

O primeiro passo aquece o app (p95 alto). Depois disso a latência fica estável.
Isso **não** substitui a corrida no staging com CPU/RAM do Render.
Comando: `python scripts/carga_staging.py --testclient`.
