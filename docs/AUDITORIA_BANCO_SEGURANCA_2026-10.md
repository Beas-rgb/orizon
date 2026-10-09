# Horizon — Auditoria do banco, integridade, isolamento e segurança

**Versão:** 1.1
**Data:** 08/10/2026
**Baseline do código:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`
**Relatório de estado:** [`RELATORIO_PASSO_0_2026-10-08.md`](RELATORIO_PASSO_0_2026-10-08.md)
**Fontes:** código do repositório, `schema-local-alembic-head-0020.sql`, dossiê técnico `banco-de-dados-horizon-b7f37e6.pdf` e `banco-de-dados-horizon-b7f37e6-dicionario.xlsx`. O SQL, o PDF e a planilha não estão neste repositório.

## 1. Limites desta auditoria

**Estado de execução:** este pacote é revisão documental do snapshot e dos artefatos recebidos. A suíte do CI, testes PostgreSQL dedicados e teste de carga **não foram executados durante o Passo 0**. “Verificado” significa inspeção de código/artefato no commit de referência; não significa exploração confirmada em produção.

O dossiê do banco declarou que a análise foi feita em cópia de leitura do repositório, com PostgreSQL local descartável, sem conexão remota ao Neon, Render ou R2. Ele registrou um conjunto de tabelas observado pelo responsável no painel Neon, mas **não confirmou que esse é o banco efetivamente utilizado pelo serviço Render**. Portanto:

- os achados de código/schema local são evidência do snapshot analisado;
- a lista de 22 tabelas é relato do dossiê sobre um banco visto no painel; esta revisão não recontou essas tabelas e não prova que esse banco é o do Render;
- nenhuma correção foi aplicada neste documento;
- nenhum teste ofensivo contra produção foi executado;
- não rodar `alembic upgrade`, `alembic stamp`, reset, seed nem teste de carga contra o banco real como parte desta auditoria.

Este documento usa “crítico” para risco potencial de perda de dados, exposição entre organizações ou quebra de anonimato. A severidade deve ser reavaliada após confirmação de ambiente e reteste.

## 2. Resumo executivo

A primeira prioridade não é feature nova: é identificar com certeza o banco conectado ao código publicado. O dossiê informa que o código espera 31 tabelas de domínio, além de `alembic_version`, enquanto a base consultada no Neon tinha 22 tabelas, sem `alembic_version`, incluindo três tabelas legadas que não fazem parte dos models atuais. A base observada não tinha tabelas essenciais ao fluxo atual, como `sessoes` e `controle_acesso`. Se o Render usar exatamente esse destino, há incompatibilidade crítica; se não usar, ainda falta reconciliar documentação e configuração.

O código apresenta proteções relevantes: Argon2id, refresh token guardado como hash, bootstrap bloqueado em `APP_ENV=production`, política central em `app/core/autorizacao.py`, validação de assinatura de arquivos, limitação de tentativas e supressão K em agregados de CLIMA. Ainda assim, o dossiê descreve riscos residuais que precisam de teste de regressão: canal lateral por timestamps, política de vínculo de usuários preexistentes, criação de conta TI, migrations que não são idempotentes, fallback de armazenamento local e script destrutivo sem guarda de ambiente.

## 3. Inventário do schema-alvo do commit analisado

O dump citado `schema-local-alembic-head-0020.sql` não está neste repositório. A tabela abaixo repete o inventário desse material externo. Não é uma comparação feita aqui entre o dump, o dossiê e o banco do Render. Diferença de tabela ou de coluna só fica confirmada quando as fontes estiverem no mesmo lugar e forem conferidas. A planilha de dicionário, também ausente do Git, agrupa 31 tabelas de domínio; as colunas completas permanecem nesses arquivos externos.

| Domínio | Tabelas do código |
|---|---|
| Identidade e controle | `usuarios`, `convites`, `sessoes`, `tokens_redefinicao`, `controle_acesso`, `pedidos_consultora`, `logs_auditoria` |
| Organização e trabalhos | `organizacoes`, `projetos`, `projeto_usuarios`, `rotulos_projeto`, `configuracoes_projeto` |
| Estrutura organizacional | `setores`, `cargos`, `perfis_funcionario` |
| Pesquisa e respostas | `pesquisas`, `perguntas`, `opcoes_resposta`, `respostas`, `tokens_resposta`, `pesquisa_participantes`, `templates_pesquisa`, `template_perguntas`, `template_opcoes_resposta` |
| Avaliação 360 | `ciclos_avaliacao`, `avaliacao_relacionamentos`, `avaliacao_respostas` |
| Biblioteca | `documentos` |
| Mensagens | `notificacoes`, `entregas_mensagem` |
| Laboratório | `cenarios_lab` |

### 3.1 O que a planilha do schema documenta

O workbook contém três abas: `dicionario`, `matriz_modulo_tabela` e `rotas`. Elas são importantes para revisão porque relacionam colunas e domínios, módulos de código que leem/escrevem tabelas e rotas HTTP com seus serviços. Na próxima auditoria de código, esse mapeamento deve virar checklist verificável: para cada rota, validar papel global, escopo no projeto, estado do recurso, tenant, operações de leitura/escrita, efeitos colaterais e exposição na resposta.

### 3.2 Integridade referencial

O dossiê informa referências sem FK e ausência de regras `ON DELETE` em cascata. **Não adicionar FKs em lote sem pré-trabalho.** Para cada referência:

1. identificar o relacionamento esperado e quem é o owner;
2. consultar valores órfãos em staging, sem alterar dados;
3. definir a política correta de remoção/soft delete;
4. adicionar constraint com estratégia compatível com volume e disponibilidade;
5. validar a constraint em migration separada, depois de corrigir órfãos por plano aprovado;
6. testar inserts inválidos, exclusão, reativação e coexistência entre tenants.

FK não substitui autorização: um funcionário pode ter referência válida e ainda assim não pertencer ao projeto consultado.

## 4. Diferença registrada entre schema esperado e banco observado

O texto abaixo é o que o dossiê registrou. Esta revisão não reproduziu o inventário de 22 tabelas nem conferiu coluna a coluna. Não afirmar que a base observada é a de produção do Render. O dossiê fala em `neondb`, branch exibido como `Primary`, 22 tabelas e ausência de `alembic_version`. Entre as tabelas que o dossiê tratou como necessárias no código, foram registradas como ausentes:

- `controle_acesso`
- `pedidos_consultora`
- `sessoes`
- `tokens_redefinicao`
- `cargos`
- `perfis_funcionario`
- `rotulos_projeto`
- `pesquisa_participantes`
- `ciclos_avaliacao`
- `avaliacao_relacionamentos`
- `avaliacao_respostas`
- `cenarios_lab`

Também foram anotadas tabelas legadas, sem estrutura/colunas confirmadas no dossiê: `ia_conversas`, `ia_mensagens` e `projeto_documentos`. Não assumir que essas tabelas podem ser apagadas ou reaproveitadas antes de descobrir sua origem e verificar se contêm dados úteis.

### 4.1 Procedimento obrigatório de reconciliação

1. **Congelar operações de schema**: não executar reset, `stamp` ou upgrade automático.
2. Registrar o SHA do commit implantado e a URL/branch do deploy, sem coletar nem expor segredos.
3. No painel Render, comparar o destino lógico de `DATABASE_URL` e `DATABASE_URL_DIRECT`: projeto/host, database, usuário de conexão e branch de Neon; mascarar a senha em toda evidência.
4. Conferir nos logs o SHA implantado, `ALEMBIC_HEAD`, mensagem de migração e falhas de boot. A resposta pública de health não deve revelar host, nomes de schema, tokens ou stack trace.
5. No Neon, em consulta somente leitura no branch que o serviço realmente usa, registrar `current_database()`, `current_schema()`, a existência de `alembic_version`, `version_num`, lista de tabelas, tamanho do banco e data do último restore conhecido.
6. Criar branch de staging a partir do ponto correto de produção; verificar restore antes de experimentar migrations.
7. Comparar `head 0020` gerado de banco descartável com o banco efetivo; produzir diff de tabelas, colunas, tipos, índices, uniques, FKs, defaults e constraints.
8. Escolher a recuperação somente com base no diff: upgrade de um schema versionado, baseline/restamp validado, migração de legado ou restauração de destino errado. `alembic stamp head` é proibido enquanto não houver prova de que o schema já corresponde ao head.
9. Executar o procedimento aprovado em staging, testar login/trabalhos/pesquisas/documentos e somente depois preparar uma janela de produção com backup, plano de interrupção e rollback.

## 5. Matriz de risco e ação

Legenda de estado: **VERIFICADO NO SNAPSHOT** = observado diretamente no código/artefato analisado; **RELATADO / NÃO REPRODUZIDO** = consta do dossiê ou é hipótese plausível ainda sem reteste independente; **PENDENTE DE AMBIENTE** = exige confirmação do destino/configuração efetiva; **SEM EVIDÊNCIA DE TESTE** = não há execução registrada neste Passo 0.

| ID | Gravidade | Estado da evidência | Achado / evidência a revalidar | Ação exigida | Teste de aceite |
|---|---|---|---|---|---|
| DB-01 | **Crítica** | PENDENTE DE AMBIENTE | Schema consultado no Neon não corresponde ao que o código espera; destino do Render não confirmado | Identificar destino e reconciliar schema em staging | Login e fluxo de leitura/escrita passam no banco certo; diff salvo; nenhum dado perdido |
| DB-02 | **Alta** | VERIFICADO NO SNAPSHOT | `_revisao_atual()` em `app/core/migracao.py` trata qualquer erro de consulta à `alembic_version` como `None` | Distinguir marcador ausente de erro de conexão/permissão/schema; falhar fechado | Falha de conexão não inicia migration; ausência do marcador produz erro seguro e instrução de recuperação |
| DB-03 | **Alta** | PENDENTE DE AMBIENTE | `DATABASE_URL_DIRECT` pode apontar para destino diferente da URL de aplicação | Validar destino/branch de ambas antes de migrar | Teste de preflight rejeita nomes/destinos divergentes sem exibir credenciais |
| DB-04 | **Alta** | RELATADO / NÃO REPRODUZIDO | Migrations `0012` e `0020` não são idempotentes segundo experimento do dossiê | Escrever testes de recuperação em PostgreSQL descartável; escolher caminho explícito de baseline/forward fix | Fluxo de banco vazio e fluxo legado aprovado passam em CI; nenhum `stamp` cego |
| SEC-01 | **Crítica** | VERIFICADO NO SNAPSHOT | `scripts/reset_manter_ti.py` apaga muitas tabelas e não tem guarda forte de ambiente/flag | Desativar/recusar `APP_ENV=production`, exigir confirmação nominal e limitar URL a staging/local; preferir remover do uso cotidiano | Teste unitário prova abortar se production ou URL não autorizada; CI verifica script protegido |
| SEC-02 | **Crítica** | RELATADO / NÃO REPRODUZIDO | Importação busca usuários preexistentes por e-mail e usa o resultado para vínculos/perfis; dossiê marca risco cross-tenant | Proibir vínculo implícito; política de reconciliação exige consentimento/autorização e papel compatível no projeto | Conta de outro projeto/tenant não é associada nem alterada por importação; permanece tudo íntegro após rejeição |
| SEC-03 | **Crítica** | RELATADO / NÃO REPRODUZIDO | Dossiê relata correlação de resposta anônima por timestamps idênticos entre resposta, token e participante | Quebrar correlação temporal; minimizar timestamps detalhados e metadados acessíveis; auditar sem usuário; rever logs | Teste de banco e payload não permitem associar resposta CLIMA a pessoa por chave/timestamp/ID; K aplicado |
| SEC-04 | **Alta/Crítica** | RELATADO / RETESTE OBRIGATÓRIO | Papel TI pode estar convidável por consultora quando não há TI, conforme caminho de convite do snapshot | Somente administrador TI existente/bootstrapping autorizado pode conceder papel privilegiado; não confiar em papel pedido no payload | Consultora não consegue convidar TI; corrida cria no máximo uma conta; auditoria não registra segredos |
| SEC-05 | **Alta** | REVALIDAR CONFIGURAÇÃO | Fallback de R2 para disco local pode atuar se configuração estiver incompleta | Em produção, falhar no boot se R2 não estiver validado; disco local permitido só em ambiente explicitamente local/teste | Configuração sem R2 falha no preflight de production; teste de upload/download em R2 staging |
| SEC-06 | **Alta** | VERIFICAR ROTINAS RELACIONADAS | A rotina `reset_manter_ti.py` contém nomes legados e não cobre de forma uniforme todo schema | Mapear todas as rotinas de DELETE/UPDATE manual e automáticas; proibir reset sem backup e janela | Scanner/checklist de mutações destrutivas; restore de staging exercitado |
| SEC-07 | **Alta** | RELATADO NO DOSSIÊ | O dossiê cita 14 colunas de referência sem FK e retenção que apaga auditoria após prazo | Inventariar relações e política de retenção; limpar órfãos com aprovação e migrações | Nenhuma FK inválida; política de retenção aprovada e teste de restauração/auditoria |
| SEC-08 | **Alta** | RISCO A COBRIR EM TESTES | `usuario_id` em perfil/importação deve ser validado no mesmo projeto | Todas as operações usam política de projeto e checagem de ativo/deleted_at | Matriz A/B para UUID de outros projetos retorna 404 sem efeito colateral |
| SEC-09 | **Alta** | RISCO A VALIDAR EM TESTES | Resposta de erro, link de primeiro acesso e logs são superfícies de segredo | Redação automática para senha, JWT, refresh, links com token, URL de banco e PII | Capturar logs/JSON em testes de erro e confirmar ausência de segredo |
| SEC-10 | **Média/Alta** | LACUNA INDICADA NO SNAPSHOT; RETESTAR | JWT de acesso pode sobreviver ao logout até expirar, mesmo com refresh revogado | Planejar `jti`/`session_id` com validação ou outra revogação com custo medido; revogar em troca de senha | Token usado após logout/troca de senha não pode executar operações protegidas conforme a política adotada |
| SEC-11 | **Alta** | SEM EVIDÊNCIA DE TESTE MULTI-WORKER | Rate limit em processo/conta/IP deve resistir a vários workers e proxy incorreto | Rate limit por rota, conta normalizada, IP validado e limites globais; confiar só em proxies configurados | IP forjado não burla limite; duas instâncias não zeram a proteção; limites não permitem bloqueio trivial do usuário |
| SEC-12 | **Alta** | SEM EVIDÊNCIA DE TESTE ADVERSARIAL | Upload valida alguns bytes MIME, mas precisa resistir a arquivos ZIP/XML maliciosos e arquivos compactados expansivos | Validar MIME e estrutura; limites de bytes/descompressão/páginas; quarentena; parser isolado e atualizado | Fixtures benignas/maliciosas, zip bomb controlado, XML externo bloqueado, parser sem travar API |
| SEC-13 | **Alta** | SEM EVIDÊNCIA DE MATRIZ E2E COMPLETA | Segurança da biblioteca depende do mesmo controle de tenant/visibilidade no download, listagem e update | Centralizar política, `Content-Disposition` seguro, `nosniff`, armazenamento privado e URLs temporárias quando adequado | Matriz papel × visibilidade × estado × objeto; IDs de outros tenants retornam 404 |
| SEC-14 | **Alta** | VERIFICADO NO FRONTEND DO SNAPSHOT; XSS NÃO DEMONSTRADO | Risco de XSS comprometer tokens guardados em `sessionStorage` | CSP rigorosa, saída escapada, sem HTML não confiável, revisão de dependências; avaliar cookie HttpOnly/Secure/SameSite com desenho de origem | Testes de UI e headers; nenhuma string de documento é renderizada como HTML executável |
| SEC-15 | **Alta** | SEM EVIDÊNCIA DE RESTORE OPERACIONAL | Sem evidência de restauração operacional completa no pacote analisado | Criar política de backup, restore, criptografia, retenção e teste recorrente | Evidência de restore com tempo medido e contagem/checksum validado |

## 6. CLIMA: privacidade precisa ser uma propriedade do sistema inteiro

O snapshot apresenta separação de token para os tipos anônimos e o painel usa `K_ANONIMATO` para suprimir resultados abaixo de K. O dossiê, porém, relata possível correlação temporal entre resposta, token e participante. Esse canal lateral **não foi reproduzido de forma independente no Passo 0**; até que testes de banco, payload, logs, filtros e exportações demonstrem o contrário, o anonimato deve continuar como risco crítico em aberto.

Regras finais:

1. `K_ANONIMATO` deve ter valor documentado (atualmente a documentação cita K=5) e ser aplicado a cada dimensão, filtro, exportação, relatório e endpoint.
2. Não retornar lista nominal de participantes CLIMA nem estado `EM_ANDAMENTO` associado a pessoa.
3. Não armazenar chave direta entre pessoa e resposta de CLIMA.
4. Evitar timestamps exatos coincidentes em tabela de respostas, token anônimo e estado do participante. Não usar microsegundos ou IDs como canal lateral.
5. Auditoria registra o evento de modo que não reidentifique o respondente; logs de API não devem guardar resposta textual ou token.
6. Texto livre requer política específica para redação de PII; analisar comentários em grupo pequeno deve ser suprimido ou agregado com revisão apropriada.
7. A avaliação 360/performance não é anônima por padrão; sua visibilidade e mínimo por perspectiva precisam de regras separadas.
8. A interface precisa dizer com precisão o que é anonimizado e quais metadados são mantidos; não usar a palavra “anônimo” até a revisão e os testes serem aprovados.

## 7. Modelo de ameaça defensivo

| Superfície | Abuso a impedir | Controle obrigatório | Teste defensivo |
|---|---|---|---|
| Login/recuperação | força bruta, password spraying, enumeração de e-mail | resposta uniforme, Argon2id parametrizado, rate limit por conta/IP, tempos e logs seguros | lote de tentativas sintéticas, conta inexistente vs real, IP forjado |
| JWT/refresh | token roubado, refresh replay, sessão antiga | expiração curta, refresh rotacionado/revogado, token nunca em logs, política de revogação access | replay, logout, troca de senha, token expirado |
| Autorização API | IDOR/BOLA, mudança de ID em URL/body, papel manipulado | conferir usuário + papel + vínculo + tenant + estado + operação no backend; resposta 404 uniforme para recurso alheio | matriz consultora A/B, órgão A/B, funcionário A/B, TI |
| SQL/ORM | SQL injection em filtros, busca ou relatórios | query parametrizada; proibir interpolação de input em `text()`/SQL; allowlist para ordenação/campos | testes de payload inocuo que verifica rejeição/parametrização; análise estática |
| Importação CSV/XLSX | e-mail de outro tenant, hierarquia arbitrária, duplicata, ciclo, fórmula/CSV injection em export | validação no servidor na prévia e confirmação; papel e vínculos compatíveis; escape de campos exportados para planilha | arquivo sintético com duplicata, ciclo, cross-tenant, cabeçalho inesperado e fórmula |
| Biblioteca/R2 | disfarçar HTML, traversal, arquivo excessivo, objeto privado acessível | MIME real, tamanho e estrutura, chave de objeto interna, tenant/visibilidade na leitura, bucket privado | MIME divergente, nome/path malicioso, tentativa cross-tenant, objeto inexistente |
| Parser documental | ZIP/XML bomb, arquivo especialmente construído, injeção de instruções por documento | quarentena, limites de descompressão, parser isolado, timeout, arquivo não confiável não vira instrução | corpus adversarial sintético em ambiente isolado, tempo/memória máximos |
| Frontend | XSS, dependência comprometida, token acessível por JS | CSP, saneamento/escape, nenhuma execução de conteúdo de usuário, lockfile e audit, sessão curta | teste de conteúdo HTML, scan dependências, headers de segurança |
| E-mail/convites | abuso em massa, link de primeiro acesso em JSON/log, phishing por destino aberto | token one-time hashed, expiração, allowlist de origem, rate limit, logs redigidos | testar falha de e-mail, URL `next`, token reaproveitado e convite expirado |
| Rotinas de manutenção | reset/cleanup em banco errado | ambiente allowlist, confirmação explícita, least privilege, backup, modo dry-run | teste que recusa produção por ambiente e por host/database não autorizado |
| IA / RAG | prompt injection indireto, citação inventada, dados de outro órgão | documentos como dados não confiáveis, retrieval com tenant filter, ferramentas read-only, saída com schema e citação validada | corpus sintético com instruções maliciosas, tentativa de recuperar outro tenant, resposta sem evidência |
| Disponibilidade | abuso de upload, login, geração de token, query cara | rate limit, timeout, limite de payload, paginação, quotas, proteção no edge e orçamento de query | teste gradual em staging, não em produção |

O objetivo não é afirmar que toda classe está atualmente explorável. A tabela é o modelo de ameaça que precisa guiar testes e correções antes da produção com dados reais.

## 8. Banco: migration, integridade, desempenho e retenção

### 8.1 Migrations

- Não editar retroativamente migrations aplicadas a ambientes compartilhados sem decisão específica e prova de histórico.
- Testar em PostgreSQL descartável: banco vazio → head, banco legado aprovado → estratégia de baseline, upgrade a partir de cada revisão suportada e downgrade apenas quando seguro.
- Tornar o runner explícito: falha de conexão/permissão não equivale a ausência do marcador Alembic.
- Conferir que a URL de migration e a URL de runtime apontam para o mesmo destino lógico.
- O boot da API não deve tentar “adivinhar” que um schema não versionado é vazio. Preferir job de release/migration controlada, executado uma vez antes do rollout.
- O plano de rollback deve contemplar incompatibilidade entre versão antiga/nova e schema expandido; usar padrão expand-contract para alterações que exigem deploys separados.

### 8.2 Índices e consultas

Não criar índice porque uma coluna “parece importante”. Para cada índice novo, registrar query real, `EXPLAIN (ANALYZE, BUFFERS)`, seletividade, custo de escrita, tamanho e plano de rollback. Rever índices ausentes no dossiê, especialmente colunas usadas em listas/filtros de projetos, pesquisas, respostas, tokens e convites, conforme query plan real. Não executar `EXPLAIN ANALYZE` de consultas potencialmente pesadas no ambiente real sem janela autorizada.

### 8.3 Integridade e limpeza

- Tabelas com `deleted_at` não devem ser interpretadas como apagadas fisicamente; todos os fluxos de negócio precisam excluir registros soft-deleted conforme política.
- O job de manutenção não pode apagar evidência obrigatória, dados ainda vinculados ou linhas exigidas para investigação.
- Definir retenção por finalidade: sessões/tokens, logs de segurança, eventos de negócio, respostas de pesquisa e documentos. Período de auditoria não deve ser decidido só por conveniência técnica.
- Criar relatório dry-run para cada operação de limpeza: contagem por tabela, corte temporal, critérios, amostra de IDs mascarados e aprovação antes do DELETE.

## 9. Critérios de encerramento da auditoria

A auditoria documental não será marcada como encerrada enquanto o destino efetivo do Render não for confirmado e as correções críticas não tiverem teste reproduzível no snapshot atualizado. O CI existente é evidência de infraestrutura de teste, não resultado de execução deste Passo 0.

- [ ] Confirmado qual Neon database/branch o serviço Render usa.
- [ ] Schema diff de produção/staging para `head 0020_lab` anexado, com origem e timestamp.
- [ ] Script de reset bloqueado em produção e com confirmação em staging.
- [ ] Política de conta TI e de importação cross-tenant testada.
- [ ] CLIMA validado contra associação direta e canais laterais.
- [ ] Migrations em fluxo de recuperação comprovado; nenhum comportamento de “schema vazio por erro”.
- [ ] R2 obrigatório em production, objetos privados e política de exclusão/orfandade.
- [ ] Backup/restore testado.
- [ ] Matriz de autorização de todos os recursos sensíveis coberta por testes.
- [ ] Relatórios do CI (`pytest`, Ruff, `pip-audit`, npm build/lint/test) anexados ao PR de cada correção.
