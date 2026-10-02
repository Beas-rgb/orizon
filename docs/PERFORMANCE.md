# Desempenho

## Baseline do banco

Ainda não medido no Neon. O inventário de staging da Fase 0 não rodou.

## Latência e região

Ainda não medidas no painel. `GET /health/db` ainda não devolve `latencia_ms`.

## Orçamento de consultas

Medido no SQLite dos testes, depois da Fase 2:

- `GET /auth/eu`: 1 consulta.
- `GET /projetos`: no máximo 6.
- `GET /projetos/{id}`: no máximo 7.

O login não segura a conexão do banco enquanto calcula o hash.

## Memória do hash

Estimativa do plano, não medida neste Free: 16 logins ao mesmo tempo, com 64 MiB cada, somavam cerca de 1.025 MiB. Agora o teto é 2 hashes ao mesmo tempo.

## Carga

Vazia até a Fase 9. Nenhum número daqui é capacidade do Render nem do Neon.
