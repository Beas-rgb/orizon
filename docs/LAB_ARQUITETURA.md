# Laboratório — decisão de arquitetura (adendo B.8)

**Decisão: C (híbrido).**

- Demonstração pequena (até `LAB_MAX_PARTICIPANTES`, padrão 1000, sementes 10–600) no banco principal só depois do isolamento por `origem=SINTETICO` + `tipo_conta` + e-mail `@sintetico.invalid` comprovado nas rotas.
- Volume, concorrência e as sementes 500/600 ligam `STAGING_DATABASE_URL` (hoje configurável e ainda sem uso de carga). Produção recusa `ENABLE_LAB=true`.
- Limpeza: dry-run obrigatório; exclusão só apaga `origem=SINTETICO`. Registro `NORMAL` nunca entra na cascata.

Por que não A: o isolamento lógico ainda não foi medido em toda rota com volume. Por que não B puro: a consultora precisa demonstrar no mesmo produto, em escala pequena, sem um segundo deploy.

Pendência humana: branch Neon de staging ou `STAGING_DATABASE_URL` apontando para base descartável — nunca para o destino do Render.
