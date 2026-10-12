# HORIZON — Plano Mestre de Engenharia e Produto até o “Efeito Smartphone” e 50 mil usuários/mês

**Versão:** 1.1
**Data:** 08/10/2026
**Baseline de código/documentação:** repositório `Beas-rgb/orizon`, commit `b7f37e6e475ff5401df0b60744b21955bbcea52f`
**Relatório de Passo 0:** [`RELATORIO_PASSO_0_2026-10-08.md`](RELATORIO_PASSO_0_2026-10-08.md)
**Fontes adicionais:** `schema-local-alembic-head-0020.sql`, `banco-de-dados-horizon-b7f37e6.pdf` e `banco-de-dados-horizon-b7f37e6-dicionario.xlsx` enviados pelo responsável do projeto. Esses três arquivos não estão neste repositório. São materiais externos. Os números 21 (contexto mestre antigo), 22 (dossiê) e 31 (dump citado) ainda não foram reconciliados com fontes comparáveis. Nenhum deles prova qual banco o Render usa. 50 mil usuários por mês continua meta de validação, não capacidade comprovada.

> **Regra de leitura:** “observado” significa que a informação aparece no código/documento analisado; “confirmar em ambiente” significa que é necessário olhar o alvo efetivo no painel/logs; “meta” significa resultado desejado, ainda não demonstrado. Este plano não é certificado de segurança nem prova de capacidade produtiva.

## 1. Visão e resultado de negócio

O Horizon deve evoluir de uma plataforma que organiza trabalhos, pesquisas, estrutura organizacional e avaliações para uma plataforma operacional e analítica da consultoria de Gestão de Pessoas. Ele deve ajudar a consultora a conduzir o ciclo completo de um trabalho:

**entrada de dados e documentos → preparação da estrutura → aplicação de instrumentos → validação e estatística → achados e evidências → diagnóstico → plano de ação → relatório → acompanhamento e histórico.**

O diferencial pretendido não é apenas possuir mais telas do que o YESPER. É reduzir o trabalho manual necessário para consolidar dados, procurar documentos, comparar ciclos e redigir entregáveis, com rastreabilidade suficiente para a consultora revisar e defender cada conclusão.

### 1.1 O que significa “efeito smartphone”

O Horizon alcança esse marco quando a consultora consegue, em um trabalho real e autorizado:

1. importar dados de uma equipe e revisar a prévia de forma segura;
2. executar pesquisa e/ou avaliação de ponta a ponta;
3. abrir resultados sem esperar consultas excessivas nem exportar planilhas para juntar tudo manualmente;
4. localizar evidências em documentos do próprio órgão e no histórico que ela tem autorização para consultar;
5. receber achados com números reproduzíveis, fonte, amostra, método, limitações e próximos passos;
6. preparar um relatório profissional com poucos ajustes, mantendo a decisão final humana;
7. revisar o histórico do trabalho sem reconstruir toda a memória do projeto;
8. saber que os dados de outro órgão não serão acessados, misturados ou usados para análise sem permissão.

O produto não deve prometer que a IA “sabe tudo”, decide promoção/penalidade ou prova causalidade a partir de correlação. Seu diferencial precisa ser confiança, economia de tempo e qualidade do trabalho entregue.

## 2. Meta de capacidade: 50 mil usuários por mês

A meta de longo prazo é **50.000 usuários distintos/ativos no mês**, não 50.000 usuários simultâneos. O primeiro perfil mensal de validação deve ser o cenário mais realista discutido, aproximadamente **10.000 usuários/mês**, e só depois avançar para 50 mil. São métricas diferentes. Ainda é necessário definir, com base no modo real de uso, quantas pessoas podem abrir links e responder dentro da mesma hora, quantas consultoras trabalham em painéis ao mesmo tempo e quantos documentos/relatórios são processados em cada pico.

O sistema só poderá declarar capacidade depois de executar testes de carga contra um ambiente de staging equivalente à infraestrutura paga planejada, usando o fluxo real (login, leitura de trabalho, formulário, envio de resposta, painel, biblioteca e jobs). Testar apenas `/health` prova que o endpoint simples responde; não prova capacidade do banco, autorização, upload, envio de respostas ou geração de relatórios.

Referência detalhada: [`PLANO_ESCALA_VALIDACAO_50K.md`](PLANO_ESCALA_VALIDACAO_50K.md).

## 3. Baseline técnico observado

### 3.1 Stack a preservar

- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS 4, React Router; código oficial em `frontend/`.
- **API/domínio:** Python 3.12 + FastAPI.
- **Persistência:** SQLAlchemy 2.x com driver síncrono `psycopg`.
- **Banco:** PostgreSQL no Neon; Alembic para migrations.
- **Arquivos:** Cloudflare R2 via cliente compatível com S3.
- **Hospedagem descrita:** frontend no Cloudflare Pages; API em Render; banco Neon; objetos em R2.
- **Autenticação:** JWT de acesso curto + refresh opaco armazenado como hash; senha com Argon2id; proteção de tentativas em `controle_acesso`.
- **Qualidade:** pytest, Ruff, testes de frontend com Vitest/TypeScript/Oxlint; CI inclui Postgres 16, `alembic upgrade head`, `pytest`, Ruff, `pip-audit`, `npm ci`, build, lint e Vitest.

Não há motivo demonstrado para uma reescrita em Java, troca de framework, adoção imediata de microserviços ou criação de uma infraestrutura distribuída complexa. Primeiro, fechar discrepâncias do banco, segurança, qualidade de fluxos e medição real.

### 3.2 O que já existe no código analisado

O repositório contém fluxos para autenticação, convite e primeiro acesso, consultora/projeto, organizações, importação de CSV/XLSX, setores/cargos/perfis de funcionários, hierarquia, pesquisas, perguntas, respostas, painel agregado, ciclos e relações de avaliação, biblioteca documental, notificações, laboratório de cenários e painéis por papel. A autorização centralizada `app/core/autorizacao.py` já existe. O frontend oficial tem lazy loading para páginas, estado de sessão com tentativa de reconexão e telas responsivas.

A presença de um componente visual ou de uma rota não é prova de que todo fluxo esteja pronto para produção. Os critérios de aceite abaixo exigem integração real, testes negativos, observabilidade e evidência do resultado.

### 3.3 Limites atuais conhecidos

- A documentação existente indica `configuracoes_projeto.ia_modo = DESATIVADA`; não se deve tratar o Gerente Horizon como implementado.
- O painel da consultora observado em `InicioConsultoraNovo.tsx` lista trabalhos e agrega estados; isso não é ainda um motor analítico que cruza dados, documentos e histórico.
- `SmartBriefing.tsx` é um componente de apresentação; a existência do componente não prova integração com análises de backend.
- A camada de biblioteca guarda documentos e metadados, mas o pipeline completo de extração, indexação, recuperação com citações e avaliação de respostas ainda precisa ser construído.
- Não há evidência, nestas fontes, de testes Playwright/E2E de navegador cobrindo todos os papéis.
- Não há medição de carga de produção/staging que prove 50 mil usuários ativos/mês ou 5 mil concorrentes.
- A topologia real de banco usada pelo Render ainda precisa ser reconciliada com o banco que foi inspecionado no painel Neon.

## 4. Ordem de prioridade obrigatória

### P0 — segurança e integridade antes de dados reais

1. **Confirmar o banco efetivo da API.** O dossiê do banco analisou o commit citado e registrou um banco consultado no Neon com 22 tabelas, sem `alembic_version`, enquanto o código espera 31 tabelas de domínio mais o marcador. O próprio dossiê diz que não conectou ao Render e não confirma que esse banco é o destino da aplicação. Não executar migração/reset até essa relação ser comprovada.
2. **Bloquear a rotina destrutiva de reset.** `scripts/reset_manter_ti.py` apaga conjuntos extensos de tabelas e não contém trava de ambiente/flag de confirmação equivalente à criticidade da operação. Torná-lo inutilizável em produção por construção, exigir confirmação explícita em não produção e cobrir com testes de proteção. Até lá, não executar.
3. **Corrigir e testar isolamento em importação e vínculo de pessoas.** Um e-mail já existente não deve ser automaticamente anexado a outro projeto/tenant sem política explícita, validação de papel, autorização e confirmação. A confirmação de importação deve continuar revalidando tudo no backend.
4. **Fechar o canal lateral do anonimato CLIMA.** Mesmo que o código use token separado e suprima agregados abaixo de K, o dossiê relata timestamps iguais que podem permitir correlação com o estado individual do participante. Desacoplar metadados temporais, status, auditoria e respostas; manter K mínimo em todos os meios de saída; validar exportações futuras.
5. **Revisar criação de contas TI.** Verificar quem pode emitir convite com papel `TI`; o convite de conta privilegiada deve ser provisionado exclusivamente pelo fluxo administrativo autorizado, com proteção contra corrida e auditoria.
6. **Fail-closed para migrations.** Ausência ou erro ao ler `alembic_version` não deve ser tratado automaticamente como banco novo. Detectar esquema incompatível e parar com diagnóstico sem segredos. Validar `DATABASE_URL` e `DATABASE_URL_DIRECT` para provar que aplicação e migrations apontam para o mesmo banco/branch.
7. **R2 obrigatório em produção.** O código tem fallback para disco local se as variáveis R2 não estiverem completas. Em ambiente com disco efêmero, isso pode fazer documentos desaparecerem após reinício/deploy. Produção deve falhar no boot se o backend de objetos não estiver configurado e verificado.
8. **Backups e restauração comprovados.** Registrar backup/PITR, retenção, restauração em ambiente isolado, RPO/RTO desejados e responsável por aprovar retorno.

Detalhamento e testes: [`AUDITORIA_BANCO_SEGURANCA_2026-10.md`](AUDITORIA_BANCO_SEGURANCA_2026-10.md).

### P1 — qualidade e estabilidade do núcleo

- Centralizar a política de autorização e comprovar que todos os routers/services sensíveis a utilizam.
- Eliminar queries N+1, acrescentar paginação e batches onde medição/modelo mostram gargalo.
- Completar a matriz de chaves estrangeiras e constraints após inventário de órfãos; nunca criar FK cega sobre dados legados.
- Revisar idempotência de submissão, convite, importação, publicação e tarefas; concorrência não pode criar duplicatas.
- Remover I/O de e-mail, R2, extração de arquivos e LLM de requests longas; usar tarefas duráveis, retries e idempotência.
- Tornar logs estruturados, adicionar `request_id`/`correlation_id`, monitorar erros, latência, pool, tamanho/fila de jobs e falhas de provedores.
- Travar versões do Python em arquivo de dependências reproduzível e resolver relatórios atuais de `pip-audit`/dependências do npm no CI.
- Manter staging isolado de produção e dados de teste exclusivamente sintéticos.

### P2 — diferencial de produto e escala

- Melhorar fluxo consultora → trabalho → importação → pesquisa/avaliação → resultados → relatório.
- Biblioteca com versionamento, extração, indexação e busca baseada em evidências.
- Gerente Horizon com orquestração de estatística, Jev, busca e LLM generativo.
- Importação/exportação e migração assistida de legado/YESPER.
- Carga medida, escala horizontal de API e workers conforme os resultados justificarem.

## 5. Arquitetura alvo

```text
React + TypeScript (Cloudflare Pages)
            │ HTTPS / contratos tipados
            ▼
FastAPI (API sem estado local de negócio)
  ├─ autenticação e políticas de autorização
  ├─ serviços de domínio: trabalho, pessoas, pesquisas, desempenho
  ├─ acesso a dados SQLAlchemy / PostgreSQL
  ├─ metadados e auditoria
  ├─ integrações: e-mail, R2, provedores IA
  └─ criação de jobs duráveis para trabalho demorado
            │
            ├──────────────► PostgreSQL / Neon
            │                 fonte de verdade e histórico
            ├──────────────► Cloudflare R2
            │                 objetos privados
            └──────────────► worker separado (quando necessário)
                              extração, embeddings, relatórios, IA
```

**Princípios:** API é a fonte da verdade; React não decide autorização nem cálculo; Postgres conserva metadados, regras, versões e evidências; o conteúdo de documentos é privado; IA acessa somente o escopo autorizado; um provedor pode ser substituído por adapter; tarefas repetíveis não duplicam efeitos.

## 6. Modelo funcional e de dados

O núcleo deve permanecer centrado em `Organização`, `Trabalho/Projeto`, `Pessoa/Usuário`, `Unidade/Setor`, `Cargo`, `Perfil do funcionário`, `Documento`, `Pesquisa`, `Avaliação`, `Entregável` e `Auditoria`. Os módulos especializados devem reutilizar o mesmo projeto e as mesmas pessoas/estrutura, evitando criar segunda versão de setor, cargo, documento ou usuário para cada módulo.

O inventário do schema e os gaps de integridade estão em `AUDITORIA_BANCO_SEGURANCA_2026-10.md`. Qualquer nova entidade exige: caso de uso aprovado, owner/tenant, restrições, índices explicados, política de retenção, migration versionada, testes de integração com PostgreSQL e plano de rollback compatível com dados.

## 7. Roadmap por fases e portões

**Regra de prioridade da versão 1.1:** a ordem é bloqueante. A reconciliação do banco vem antes de mudanças no banco, releases, carga ou IA. O Gerente Analítico só começa depois das fases 0–5. A presença de documentação, código ou configuração não equivale a fase concluída; cada portão exige evidência registrada.

As fases são portões sequenciais, não estimativas de prazo nem promessas. Recalibrar a duração após cada fase conforme o tempo disponível, as falhas reais e o feedback da consultora.

### Fase 0 — Reconciliação do banco e baseline operacional (bloqueadora)

**Objetivo:** confirmar com evidência qual commit e banco o serviço implantado realmente usa e como recuperar os dados.

- registrar SHA/serviço/região e data do deploy, sem segredo;
- comparar o destino lógico de `DATABASE_URL` e `DATABASE_URL_DIRECT` no Render com o projeto/database/branch do Neon observado;
- conferir logs de boot e revisão Alembic esperada/real sem expor host privado, URI, tokens ou stack trace;
- capturar schema remoto somente leitura e comparar tabelas, colunas, tipos, defaults, índices, uniques, FKs e constraints com o dump local do head 0020;
- criar/validar staging isolado e demonstrar restore antes de experimentar recuperação;
- documentar a decisão de recuperação (upgrade, baseline validado, migração de legado ou destino incorreto) com plano de rollback.

**Não fazer nesta fase:** executar `alembic stamp`, migration manual, reset, seed, carga ou teste destrutivo no banco efetivo. Não assumir que o Neon de 22 tabelas é o banco do Render antes de provar o destino.

**Portão:** destino confirmado; diff salvo; backup/restore testado em ambiente isolado; estratégia aprovada; nenhuma alteração de schema não autorizada.

### Fase 1 — Segurança crítica (SEC-01 a SEC-04, DB-02 e DB-03)

- bloquear `scripts/reset_manter_ti.py` em produção, limitar destinos aceitos a local/staging autorizado e exigir confirmação explícita; nunca o usar como rotina comum;
- impedir vínculo implícito cross-tenant por e-mail durante importação;
- testar e quebrar possíveis canais de correlação do anonimato CLIMA, incluindo timestamp, token, participante, status, log, dashboard e exportação;
- permitir concessão do papel TI apenas por fluxo administrativo autorizado, validando autorização no servidor;
- fazer o runner de migration distinguir marcador ausente de erro de conexão/permissão e falhar fechado;
- validar que `DATABASE_URL` e `DATABASE_URL_DIRECT` apontem para o mesmo destino lógico antes de qualquer migration.

**Portão:** cada item tem teste automatizado que reproduz o risco antes e demonstra a correção depois; nenhum acesso cross-tenant; nenhuma operação destrutiva fora do ambiente autorizado.

### Fase 2 — Integridade e confiabilidade do backend

- provar transações atômicas e idempotência em importação, publicar/encerrar pesquisa, gravar respostas, convites e jobs;
- revisar constraints e referências sem FK; consultar órfãos em staging e só então criar migrations incrementais;
- testar upload/parser contra MIME divergente, traversal, XML/ZIP malicioso e limites de descompressão em ambiente isolado;
- confirmar que R2 é obrigatório em produção e que o fallback local só funciona em ambiente local/teste explícito;
- verificar rate limit com múltiplos workers, proxies confiáveis configurados e rotas de custo alto;
- centralizar autorização de biblioteca/download e revisar logs, erros, retenção, backup e restore;
- medir queries reais e só criar índices com plano de execução e custo de escrita documentados.

**Portão:** testes PostgreSQL verdes para schema/transação/locks; nenhuma referência nova órfã; erros/logs sanitizados; arquivos privados não cruzam tenant; restore documentado e executado.

### Fase 3 — Fluxos essenciais de produto de ponta a ponta

Provar com contas e dados sintéticos: login/recuperação/convite, criação e retomada de trabalho, importação e ajuste da estrutura, configuração/publicação/encerramento de pesquisa, resposta idempotente, avaliação, resultados agregados, biblioteca/documento e exportação/relatório mínimo.

- incluir portabilidade como requisito de primeira classe: mapeamento de campos, conflitos, IDs de origem, relatório de importação e exportação estruturada;
- não depender de esquema proprietário nem assumir acesso automático ao YESPER; migrar somente dados aos quais o responsável tenha direito de acesso;
- incluir a matriz de consultora/órgão/funcionário/TI e a matriz cross-tenant nos fluxos;
- salvar relatório de testes E2E e limitações conhecidas.

**Portão:** trabalho demonstrável do início ao fim sem passos manuais ocultos; sem estados inconsistentes, duplicatas ou exposição de dados; importação/exportação reconciliável.

### Fase 4 — Frontend e experiência operacional

- organizar a jornada ao redor de **Trabalhos**, não apenas uma coleção de módulos;
- remover indicadores fictícios e distinguir dados reais, demonstração, carregamento, sem dados, erro, sem permissão, resultado suprimido e falha temporária;
- mostrar estados de importação, conflitos, progresso, datas e próximos passos;
- garantir que downloads e mudanças sensíveis sejam autorizados pelo backend;
- cobrir login/refresh/logout, importação, pesquisa/resposta em mobile, anonimato K, permissões, downloads e falhas HTTP em E2E de navegador;
- validar teclado, leitor de tela, contraste, zoom e mobile; não fazer redesign amplo como substituto de correções P0.

**Portão:** telas principais passam nos E2E dos fluxos e papéis sintéticos; UI não inventa resultados nem revela status individual de CLIMA; experiência validada em desktop e celular.

### Fase 5 — Segurança sob carga e validação de capacidade

- preparar S0–S9 em staging com dados sintéticos e topologia paga equivalente à futura produção;
- começar pelo perfil mensal mais realista discutido, aproximadamente 10 mil usuários/mês; só depois modelar 50 mil usuários/mês;
- separar volume mensal, simultaneidade e RPS; testar campanhas, rajadas de escrita, painéis concorrentes, importações, documentos, jobs e dependências degradadas;
- medir p50/p95/p99 por rota, erros, CPU/RAM, pool, locks, query plans, jobs, R2, retries e integridade;
- dimensionar Render/Neon após evidência; não aumentar pool nem introduzir Redis, Kafka, Kubernetes ou microserviços sem gargalo mensurado;
- demonstrar backup/restore e registrar resultados de endurance.

**Portão:** rodada nominal e endurance concluídas; relatório reproduzível; integridade e segurança mantidas sob carga; custo e limites documentados. Sem evidência, não prometer 10 mil ou 50 mil como capacidade suportada.

### Fase 6 — Gerente Analítico Horizon (futuro, após o portão 0–5)

**Status atual:** planejamento; `ia_modo = DESATIVADA`; a camada analítica descrita ainda não existe como funcionalidade integrada no baseline.

- começar apenas quando as fases 0–5 tiverem portões aprovados e dados isolados por tenant;
- iniciar com um pequeno conjunto de análises determinísticas reproduzíveis, com datasets-oráculo e revisão da consultora;
- combinar motor determinístico, Jev, recuperação por fontes autorizadas e LLM generativo atrás de adapters substituíveis;
- cada achado deve mostrar evidência clicável, período, amostra, método, limitações, confiança e o que falta saber;
- documentos são dados não confiáveis; retrieval filtra tenant/permissões antes de ranquear; nenhuma ação externa ou decisão funcional é automática;
- avaliar qualidade offline, privacidade, prompt injection, citações, custo e falhas antes de liberar beta em staging.

**Portão:** nenhum dado real de outro tenant pode chegar ao contexto; toda afirmação tem evidência verificável; hipóteses são separadas de fatos; revisão humana controla relatório/plano de ação; mecanismo desativável por projeto/ambiente.

## 8. Critérios globais de “pronto”

- [ ] Nenhum P0 da auditoria de banco/segurança aberto.
- [ ] Ambiente de produção confirmado por evidência; staging separado.
- [ ] Restore de backup testado, com RPO/RTO registrados.
- [ ] Banco/migrations sem drift; nenhum reset perigoso acessível em produção.
- [ ] Matriz de autorização por papel/recurso/estado coberta por testes.
- [ ] CLIMA não permite reidentificação razoável via associação direta, timestamp, log, painel ou exportação.
- [ ] Fluxos de negócio com integração real cobertos por E2E de navegador.
- [ ] Biblioteca e geração de relatórios mantêm citação, versão e origem.
- [ ] O Gerente Analítico permanece bloqueado até que os portões das fases 0–5 sejam evidenciados.
- [ ] CI verde, dependências revisadas e artefatos de build reproduzíveis.
- [ ] Carga reporta p50/p95/p99, erros, throughput, pool, CPU/RAM, banco e R2.
- [ ] A capacidade declarada corresponde apenas aos cenários realmente medidos.

## 9. Proibições de arquitetura

- Não trocar React/TypeScript + FastAPI/Python + PostgreSQL sem problema mensurado e ADR aprovado.
- Não introduzir microserviços, Kubernetes, Kafka ou Redis apenas por previsão de usuários.
- Não implementar todas as funções típicas de RH/YESPER antes de fechar o fluxo central e seus gaps de segurança.
- Não colocar fórmula, autorização, promoção, elegibilidade ou decisão funcional dentro de prompt de IA.
- Não permitir busca/RAG que atravesse tenant por ausência de filtro.
- Não usar banco de produção para carga, teste destrutivo, seed ou pentest.
- Não tratar “CI verde”, `/health` ou milhares de registros sintéticos como prova isolada de capacidade.

## 10. Como agentes de IA devem trabalhar neste repositório

Para cada fase, criar uma conversa/tarefa separada e pedir ao agente:

1. ler este plano e o plano específico da fase;
2. inspecionar o código atual e citar arquivo + função/linha antes de afirmar estado;
3. fazer somente diagnóstico/proposta antes de modificar;
4. listar arquivos, risco, teste, migration e rollback;
5. alterar uma fatia independente; não refatorar áreas não relacionadas;
6. executar testes relevantes, Ruff/TypeScript/lint e atualizar docs;
7. apresentar diff, resultado real dos testes e limitações; nunca inventar saída de comando;
8. aguardar revisão antes de mudanças destrutivas ou de infraestrutura.

## 11. Documentos relacionados

- [`AUDITORIA_BANCO_SEGURANCA_2026-10.md`](AUDITORIA_BANCO_SEGURANCA_2026-10.md)
- [`PLANO_BACKEND_HORIZON.md`](PLANO_BACKEND_HORIZON.md)
- [`PLANO_FRONTEND_HORIZON.md`](PLANO_FRONTEND_HORIZON.md)
- [`PLANO_GERENTE_ANALITICO_IA.md`](PLANO_GERENTE_ANALITICO_IA.md)
- [`PLANO_ESCALA_VALIDACAO_50K.md`](PLANO_ESCALA_VALIDACAO_50K.md)
- relatório de baseline e documentos existentes que devem continuar sendo reconciliados: [`RELATORIO_PASSO_0_2026-10-08.md`](RELATORIO_PASSO_0_2026-10-08.md); `docs/SECURITY.md`, `docs/PERFORMANCE.md`, `docs/DATA_MODEL.md`, `docs/DEPLOY.md`, `docs/MIGRATIONS.md`, `docs/RELEASE_CANDIDATE.md`, `docs/HORIZON_CONTEXTO_IA.md`.
