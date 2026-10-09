# Horizon — Plano de evolução do backend e modelo de domínio

**Versão:** 1.1\
**Baseline:** commit `b7f37e6e475ff5401df0b60744b21955bbcea52f`\
**Relatório de Passo 0:** [`RELATORIO_PASSO_0_2026-10-08.md`](RELATORIO_PASSO_0_2026-10-08.md)
**Objetivo:** tornar a API previsível, segura, observável, testável, portable e pronta para crescer sem reescrita prematura.

## 1. Estado observado

**Execução no Passo 0:** os testes existentes não foram executados nessa etapa. O CI está configurado para usar PostgreSQL e executar Alembic/pytest/Ruff/pip-audit e verificações do frontend, mas só um registro de execução no commit atualizado comprova resultado. Não confundir presença dos testes com aprovação atual.

**Bloqueio antes de migration:** há divergência relatada entre o dump citado do head 0020 e o banco observado no painel Neon; ainda não foi confirmado que o banco observado é o destino do Render. O relatório curto `RELATORIO_PASSO_0_2026-10-08.md` não contém o procedimento completo. O detalhe está na seção 4 de `AUDITORIA_BANCO_SEGURANCA_2026-10.md`. Não aplique migration nem reset no destino efetivo até fechar o portão.

A base atual usa Python 3.12, FastAPI, SQLAlchemy 2.x, `psycopg` síncrono, PostgreSQL/Neon e Alembic. Os pacotes principais aparecem em `pyproject.toml`; a cadeia de migrations vai até `0020_lab`. Os routers ficam em `app/routers/`, lógica de domínio em `app/services/`, modelos em `app/models/`, configuração/segurança em `app/core/`, integrações em `app/integrations/` e testes em `tests/`.

Arquivos úteis existentes:

- `app/core/autorizacao.py` — política de acesso ao projeto/pesquisa/mídia;
- `app/core/deps.py` e `app/core/security.py` — identidade e credenciais;
- `app/core/database.py` e `app/core/migracao.py` — conexão e migrations;
- `app/services/identidade/` — login, convites, pedidos de consultora;
- `app/services/importacao.py` e `app/services/estrutura.py` — importação e hierarquia;
- `app/services/pesquisa/` — CRUD, respostas, desempenho, mídia, painel e modelos;
- `app/services/biblioteca.py` e `app/integrations/arquivos.py` — documentos;
- `app/services/lab/` — cenários sintéticos;
- `tests/` — testes de domínio, segurança, concorrência, banco e integrações.

**Não reconstruir esses módulos do zero.** Primeiro confirmar a versão atual, testar cada fluxo e corrigir lacunas verificadas.

### P0 operacional imediato

`scripts/reset_manter_ti.py` foi identificado no snapshot como destrutivo e sem guarda de ambiente suficiente. Até existir guard por ambiente + allowlist de destino + confirmação explícita + teste automatizado, não executar. Toda mudança desse script deve ser separada, com teste de que ele aborta em produção e ao receber URL não autorizada.

## 2. Organização alvo de código

Manter monólito modular. Separar responsabilidade sem criar camada por cerimônia:

```text
router FastAPI
  ↓ valida contrato e autentica dependências
policy/autorização
  ↓ verifica ator + recurso + tenant + estado + operação
use case / service de domínio
  ↓ transação e regra de negócio determinística
repository/queries
  ↓ SQL parametrizado, agregação, paginação
PostgreSQL / Neon

Integrações externas isoladas atrás de interfaces/adapters:
- StorageProvider (R2 e local apenas em dev/teste)
- EmailProvider
- AIProvider / JevProvider / LLMProvider
- Search/RetrievalProvider
- Job/OutboxPublisher
```

Criar repository quando há query reutilizável, grande complexidade de persistência ou utilidade para testes. Não mover toda query simples para um arquivo novo apenas para cumprir padrão.

## 3. Contratos HTTP e schemas

- Criar/usar schemas Pydantic específicos para entrada e saída; não retornar modelos SQLAlchemy diretamente.
- Cada rota precisa dizer o papel autorizado, o escopo por projeto, a regra de visibilidade, os estados permitidos e os efeitos de banco.
- Respostas de erro devem seguir contrato uniforme. Para recurso de outro tenant, retornar o comportamento não enumerável decidido pelo projeto (atualmente o padrão documentado é 404).
- Em production, nunca serializar tokens de primeiro acesso, refresh token, segredo, SQL, stack trace, URL interna de banco ou conteúdo documental desnecessário.
- Limitar tamanho de bodies, linhas, arquivo, quantidade de IDs, páginas e itens por pedido. Para exportação, aplicar exatamente as mesmas regras de privacidade da tela.
- Campos de ordenação, filtro SQL e nomes de colunas precisam vir de allowlist; não interpolar input de usuário em SQL textual.
- Contratos devem ser compatíveis com o frontend; mudanças breaking exigem rollout coordenado ou versionamento.

## 4. Autorização multi-tenant como política de domínio

`app/core/autorizacao.py` já oferece `papel_no_projeto`, `participa`, `exigir_papel`, `exigir_pesquisa_viva` e `exigir_midia_pesquisa`. A próxima tarefa não é criar outro módulo de autorização: é **garantir adoção consistente** por todos os endpoints e services sensíveis.

Cada leitura ou escrita precisa validar, no servidor:

1. identidade autenticada e ativa;
2. papel global da conta;
3. vínculo do ator com o projeto;
4. projeto e organização corretos;
5. estado atual do recurso (rascunho/publicado/encerrado/deletado);
6. visibilidade e finalidade da ação;
7. se a operação pedida está permitida para o papel;
8. se IDs relacionados (setor, cargo, superior, usuário, documento, pergunta, opção) pertencem ao mesmo projeto/tenant.

Não confiar em UUID enviado pelo cliente, botão oculto no frontend ou campo `papel` presente no body. `TI` é um papel privilegiado de operação, não deve receber acesso automático a dados de negócio por conveniência.

### 4.1 Matriz de testes obrigatória

Em cada módulo sensível, testar pelo menos:

- consultora A → recurso A: permitido conforme papel;
- consultora A → recurso B: negado sem side effects;
- órgão A → recurso A: somente permissões do órgão;
- órgão A → recurso B: negado;
- funcionário A → recurso A: somente fluxo pessoal/respostas permitidas;
- funcionário A → funcionário B/resultado individual B: negado;
- usuário desativado/deletado e recurso soft-deleted;
- papel alterado no body, IDs trocados e repetição de requisição;
- estados de rascunho, publicado, encerrado e expirado;
- pedidos concorrentes que tentem criar vínculos duplicados.

## 5. Autenticação e sessão

O código já usa Argon2id e hash de refresh token; a configuração tem acesso curto e refresh mais longo. Prioridades:

- manter política de senha/limite em backend;
- revogar refresh token em logout, mudança de senha e evento de risco;
- fechar/decidir a janela de validade do access JWT depois de logout ou troca de senha, com validação de `jti`/sessão se for necessário e viável;
- uniformizar respostas de login/recuperação para não enumerar e-mails;
- limitar tentativas por conta e IP, atrás de proxies somente quando `TRUSTED_PROXY_HOPS` estiver confirmado; nunca confiar cegamente em `X-Forwarded-For`;
- proteger endpoints de primeiro acesso, cadastro, recuperação, upload e geração de token com limites proporcionais, não só login;
- garantir one-time token opaco, expiração, hash no banco, rotação e invalidar token depois do uso;
- manter tokens fora de logs/traces/error-monitoring;
- testar concorrência, bloqueio por IP/conta e uso de token antigo;
- configurar segredos fora do repositório; validar comprimento/rotina de rotação;
- avaliar cookie `HttpOnly; Secure; SameSite` versus bearer token em `sessionStorage` apenas com desenho documentado de origem, CORS, CSRF e custo. Não mudar sessão em paralelo a uma correção crítica não relacionada.

## 6. Transações, concorrência e idempotência

Toda ação de escrita precisa declarar o seu limite transacional. Importação, publicar/encerrar pesquisa e gravar respostas não devem deixar estado parcialmente aplicado se falharem.

- Usar constraints e unique constraints como defesa final contra duplicatas, não só checagens Python.
- Fazer validação do servidor na prévia e repetir a validação na confirmação.
- Criar `Idempotency-Key` ou chave de negócio quando clientes e jobs precisarem de retries de operações caras; responder com resultado anterior em vez de duplicar.
- Lock de participante/resposta precisa cobrir corrida de dois POSTs, sem lock de sessão pelo pooler em transação quando o lock exige conexão dedicada.
- Unit tests com SQLite podem cobrir lógica, mas comportamento de FKs, locks, migrations e transações deve ser provado também em PostgreSQL.
- Exceções precisam provocar rollback explícito e resposta consistente; não logar body/token/PII.

## 7. Importação, estrutura e integridade

Fluxo alvo:

```text
upload CSV/XLSX
  → validar extensão + assinatura + tamanho/limites
  → parse isolado
  → normalizar cabeçalhos e valores
  → prévia server-side
  → detectar duplicatas, conflitos e ciclo hierárquico
  → mostrar mapeamento e impactos
  → confirmação server-side com revalidação
  → uma transação / operação idempotente
  → log de resultado + erros por linha sem PII excessiva
```

Regras:

- e-mail de usuário existente não concede vínculo automático a outro tenant;
- só reusar usuário se política de compartilhamento da conta permitir, papel for compatível e vínculo for aprovado;
- `superior_id`, setor e cargo precisam pertencer ao mesmo projeto;
- validação enviada pelo frontend não é confiável; o backend reconstrói o conjunto a partir dos valores brutos aceitos;
- impedir ciclos e hierarquias para pessoas inexistentes/inativas;
- tamanho, linhas, colunas, comprimento dos campos e tipos de células limitados;
- a exportação CSV/Excel deve neutralizar prefixos de fórmula (`=`, `+`, `-`, `@`) quando texto de usuário puder ser interpretado como fórmula pela ferramenta de destino;
- mapear linhas descartadas e razão sem revelar dados de um tenant a outro.

O valor exato de `import_max_linhas` precisa ser reconciliado entre configuração, testes e documentação; não assumir um número antigo de documento como estado atual.

## 8. Banco e migrations

### 8.1 Antes de qualquer migração real

Seguir a seção 4 de `AUDITORIA_BANCO_SEGURANCA_2026-10.md`. A discrepância entre o banco observado e o schema do código é bloqueadora. Não aplicar migration ao destino efetivo até confirmar host/database/branch, salvar baseline, testar restore e reproduzir a recuperação em staging.

### 8.2 Processo de migration

- Uma migration por mudança lógica e revisável.
- Não editar migrations antigas aplicadas só para “corrigir história”; documentar a estratégia de reparo e testar caminho legado/novo.
- Em `app/core/migracao.py`, não tratar erro de conexão/permissão/consulta de revisão como se fosse marcador ausente; falhar fechado com mensagem sem segredo.
- Validar por preflight que `DATABASE_URL` e `DATABASE_URL_DIRECT` são o mesmo destino lógico, sem imprimir credenciais.
- Migration job separado do processo web em ambiente de produção, com trava e revisão confirmada.
- Não usar `Base.metadata.create_all` nem SQL manual no Neon como atalho.
- Conferir `down_revision`, constraints, índices, defaults, soft-delete e volumetria.
- Para índices em tabelas grandes, medir e usar estratégia compatível com disponibilidade (`CONCURRENTLY` quando aplicável); testar rollback.
- Alembic precisa ter alvo de metadata coerente ou a documentação deve declarar que migrations serão 100% manuais com verificação de drift alternativa. O estado observado em `migrations/env.py` deve ser reconciliado com esse contrato.

### 8.3 Referências sem FK

O dossiê relata 14 colunas de referência sem constraint. Criar uma lista entidade → entidade, identificar órfãos em staging e decidir política para cada uma. Migrar gradualmente com verificação e `NOT VALID`/validação posterior quando apropriado. A aplicação sempre deve manter validação de tenant mesmo depois de adicionar FKs.

## 9. Consultas e performance

Prioridades, na ordem:

1. medir endpoints reais por consulta, p50/p95/p99 e perfil SQL;
2. revisar query plans no PostgreSQL com dados sintéticos de tamanho representativo;
3. reduzir N+1 com leitura em lote e agregação no banco;
4. paginação obrigatória em listas que crescem (trabalhos, usuários, participantes, documentos, eventos); máximo e default documentados;
5. evitar retornar texto documental/colunas sensíveis em listas;
6. cache somente para dados derivados e não sensíveis, com invalidation definida; nunca usar cache global sem chave de tenant/permission;
7. revisar pool baseado na soma de réplicas e limites do Neon, não só no número de requests.

Não criar índice sem query alvo; cada índice deve citar evidência de `EXPLAIN`, impacto em escrita e como será monitorado.

## 10. I/O externo e tarefas duráveis

Extração, geração de relatório, e-mail, objetos R2 e IA são operações lentas ou falíveis; não devem segurar a transação do usuário nem pool de banco mais do que o necessário.

- separar gravação no banco de chamada ao provedor externo;
- usar `outbox`/job persistente quando a entrega precisar sobreviver a reinício ou retry;
- status de job: `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `FALHA`, `CANCELADO`, com tentativas, `next_attempt_at`, erro sanitizado e `idempotency_key`;
- worker separado só quando existir necessidade real, com escala e limites independentes da API;
- retries exponenciais com jitter, limite máximo e fila de falha para investigação;
- não manter bytes grandes em memória indefinidamente; stream, limite de tamanho e cleanup de URL/object buffers;
- toda chamada externa tem timeout, budget de retries, correlação e fallback seguro;
- se o job de IA falhar, o trabalho e os resultados determinísticos continuam disponíveis.

## 11. Biblioteca e RAG

O domínio de documentos começa em `documentos`, com metadados e chave de armazenamento. O backend futuro precisa suportar versionamento, extração e referência precisa a evidência:

- `Document` + `DocumentVersion`/hash de conteúdo;
- estado `RECEBIDO → QUARENTENA → EXTRAINDO → INDEXADO` ou `ERRO`;
- preservação de localização da fonte (página PDF, seção, folha/intervalo XLSX, parágrafo DOCX);
- chunk indexado com tenant/projeto/documento/versão/permissão;
- resultados de recuperação guardam `SourceCitation` com página/section e fragmento limitado;
- remoção/retificação do documento invalida vetores/índices derivados;
- documento é dado não confiável, nunca instrução do agente;
- retrieval sempre aplica o escopo de permissões antes de calcular ranking;
- exportar o conteúdo original e metadados sem dependência de provedor específico.

Detalhamento IA em `PLANO_GERENTE_ANALITICO_IA.md`.

## 12. Integrações substituíveis

Criar fronteiras para `StorageProvider`, `EmailProvider`, `AIProvider`, `JevProvider`, `LLMProvider` e mecanismo de busca. Regras:

- o domínio não importa SDK de provedor diretamente;
- segredo em variável de ambiente ou secret manager;
- timeout, retries, custo e erros padronizados;
- telemetria de sucesso/falha/custo sem prompts ou PII em logs por padrão;
- saída estruturada validada com schema quando for consumida pelo sistema;
- se o provedor ficar fora, usuário vê estado de degradação e pode seguir com estatística determinística.

## 13. Observabilidade e auditoria

Cada operação importante deve ter `request_id`/`correlation_id` e, se for job, `job_id`. Medir:

- latência por rota (p50/p95/p99), status HTTP e erro;
- espera/timeout de pool, conexões, SQL lenta e lock wait;
- duração e falhas de e-mail, R2, importação, extração, LLM;
- backlog/idade de fila, tentativas e falhas permanentes;
- tamanho de uploads/exports, quotas, rate-limit;
- tentativas de acesso negado e eventos administrativos sem capturar segredos.

Sentry pode receber stack/metadata sanitizada. Não enviar texto de resposta, senha, tokens, links de convite, conteúdo de documento nem URLs de banco. Retenção de logs deve conciliar segurança, LGPD e exigências contratuais.

## 14. Estratégia de testes do backend

Executar em ordem: análise estática/unitária; PostgreSQL descartável para schema/migrations/constraints/locks; staging para fluxos integrados. Nenhum teste destrutivo, migration experimental ou carga é executado no banco de produção.


- **Unitário:** regras puras de scoring, ciclos, validação de importação, normalização e estados.
- **Integração PostgreSQL:** constraints, migrations, transações, FK, locks, concorrência e pooling.
- **Autorização:** matriz cross-tenant em cada módulo; IDs de recursos e relações manipulados.
- **Segurança:** entrada malformada, rate limit, token expirado/replay, upload falso, XSS/HTML, SQL injection por parametrização, SSRF não permitido, path traversal e logs sem segredo.
- **Contrato:** schemas de request/response e compatibilidade do front.
- **E2E:** login → trabalho → importação → publicação → resposta → resultado → documento/relatório.
- **Carga:** somente staging, cenário completo, progressivo, com CPU/RAM/DB/R2 e erros.

### Definition of Done de cada PR backend

- [ ] Problema e impacto descritos; mudança mínima necessária.
- [ ] Teste que falharia antes e passa depois.
- [ ] Teste PostgreSQL se mexe em semântica PostgreSQL.
- [ ] Matriz de tenant/papel se toca dado protegido.
- [ ] Migration aprovada, reversível ou com estratégia expand-contract descrita.
- [ ] Ruff, pytest e auditoria de dependências relevantes executados.
- [ ] Logs/respostas livres de segredo e PII desnecessária.
- [ ] Documentação/contrato atualizado; diff revisável.
