# Escala e validação — revisão 1.1

**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Regra:** nenhum número desta página é capacidade do Render nem do Neon.

## Unidades

| Cenário | O que é | Estado em 08/10 |
|---|---|---|
| 10 mil usuários no mês | Primeiro alvo de validação mensal | Pendente. Não medido. |
| 50 mil usuários no mês | Só depois de evidência do cenário de 10 mil | Fora de escopo até lá. |
| Simultaneidade | Pedidos ao mesmo tempo | Outra métrica. O harness em `docs/CARGA_STAGING.md` recusa produção e sobe 10 → 300 em `/health`. A corrida contra staging de verdade não está preenchida. |

Misturar “usuários no mês” com “usuários ao mesmo tempo” invalida o relatório.

## O que já está escrito, e o que não é

- `GET /health/db` devolve `latencia_ms`. Medição anotada em 02/10/2026: cerca de 689 ms. É um SELECT 1 naquele momento. Não entra como SLO.
- Pool no doc de desempenho: 5 conexões e 5 de overflow no processo, 503 com `Retry-After: 3`. A auditoria de setembro falava 2/0. Não reler o painel aqui.
- Orçamento de SQL do login e da resposta foi medido no SQLite dos testes, segundo `docs/PERFORMANCE.md`. Não é tempo de Neon.
- Tabela de carga da Fase 9: vazia de propósito.

## Como uma corrida futura pode ser aceita

Só em staging, com URL que o script de carga aceite (não é `orizon-api.onrender.com`). Anotar data, cenário, usuários ou taxa, p50, p95, erro, CPU/RAM do Render e conexões do Neon. Sem esses campos, a conclusão continua “sem número de capacidade”.

O P0 do banco vem antes. Carga contra o destino errado não serve de evidência.

## O que este plano não faz

Não sobe pool, não cria índice, não liga ping e não afirma que o plano Free aguenta o mês de 10 mil.
