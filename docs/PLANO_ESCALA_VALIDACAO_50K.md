# Horizon — Plano de escala e validação para 50 mil usuários ativos/mês

**Versão:** 1.1\
**Data:** 08/10/2026\
**Status:** capacidade de produção ainda não comprovada; nenhuma execução real de carga está evidenciada no Passo 0.\
**Pré-requisito:** fechar a reconciliação do banco e os P0 de segurança antes de iniciar os cenários de carga.

## 1. Definições que não podem ser confundidas

- **50.000 usuários ativos/mês (MAU):** 50 mil identidades distintas que utilizam o produto em um mês, conforme definição de métrica a aprovar.
- **Usuários simultâneos:** usuários fazendo requisições ao mesmo tempo.
- **RPS:** requisições por segundo. Um usuário pode fazer muitas requisições.
- **Pico de campanha:** concentração de acessos após envio de convite/lembrete de pesquisa; muitas vezes mais importante do que a média mensal.
- **Pico de gravação:** milhares de funcionários podem tentar enviar resposta em uma janela curta; isso precisa ser testado no fluxo real.

O objetivo de longo prazo é 50 mil usuários mensais. A primeira referência de validação é o cenário de uso realista, aproximadamente **10 mil usuários/mês**, antes de tentar reproduzir 50 mil. Isso **não** deve ser apresentado como 10 mil ou 50 mil simultâneos sem teste específico. O volume de pico precisa ser derivado do modo real de uso e do contrato dos órgãos.

## 2. Topologia atual observada e limites

A documentação descreve frontend React/Vite servido no Cloudflare Pages, API FastAPI em Render, PostgreSQL no Neon e arquivos no Cloudflare R2. O `render.yaml` do snapshot define plano Free, pool de banco com `DB_POOL_SIZE=5` e `DB_MAX_OVERFLOW=5`, e o `Dockerfile` inicia migration antes de Uvicorn em um processo. `docs/CARGA_STAGING.md` relata medições locais de `/health`; o próprio documento diz que elas não substituem testes em staging com CPU/RAM da infraestrutura real. O dossiê do banco não comprovou o destino real usado pelo serviço.

Consequências:

- não assumir que 5+5 conexões são ideais ou suficientes sem considerar réplicas, workers, workers de job e cota do Neon;
- um healthcheck simples não mede latência do banco, locks, queries, login, upload ou submissão;
- não declarar capacidade a partir de teste com `TestClient`;
- não usar produção para gerar pico de teste;
- não iniciar escala horizontal até resolver schema/segurança e conhecer o orçamento de conexão.

## 3. Modelo de tráfego a construir

Antes de escolher infraestrutura, definir com a consultora um perfil sintético. Não incluir PII real.

| Cenário | Comportamento simulado | O que mede |
|---|---|---|
| S0 — smoke | health, readiness e login/logout de poucas contas | deploy e conexão correta |
| S1 — uso individual | consultora entra, lista trabalhos, abre trabalho e resultado | latência de leitura e autenticação |
| S2 — campanha regular | funcionários carregam formulário e submetem respostas em distribuição gradual | pool, escrita, locks, validação e duplicidade |
| S3 — rajada após lembrete | muitos clientes começam em curto intervalo | rate limit, fila, CPU/RAM, pool e retries |
| S4 — painel durante submissões | consultora abre dashboard enquanto respostas entram | concorrência entre agregação de leitura e escrita |
| S5 — importação | CSV/XLSX com tamanho/linhas representativos | parse, validação, memória, integridade |
| S6 — documentos | uploads/leituras de arquivos de tamanhos variados | R2, API streaming, limites e latência |
| S7 — job longo | extração, indexação e relatório sintético concorrentes com uso da API | isolamento do worker, fila e degradação controlada |
| S8 — endurance | carga variável sustentada por 30–60 minutos ou mais conforme cenário | vazamento de memória, acúmulo de pool/locks/fila |
| S9 — dependência degradada | R2/e-mail/LLM atrasado ou indisponível em staging | timeout, retry, fallback e disponibilidade do núcleo |

A distribuição por papel e rota deve refletir o produto real. Evitar modelo irreal em que todos os usuários acessam somente `/health` ou repetem uma única consulta barata.

## 4. Sequência de carga

**Pré-portão obrigatório:** confirmar ambiente de staging isolado, destino de banco correto, schema compatível, backup/restore e correções críticas de segurança. Se qualquer item falhar, não iniciar carga.

Primeiro construir um perfil mensal que represente aproximadamente 10 mil usuários distintos (frequência de login, respostas por usuário, janelas de campanha, uso de painéis, arquivos e relatórios). Só após o relatório dessa rodada e análise dos gargalos construir a distribuição de 50 mil/mês. Volume mensal e concorrência são provas diferentes.

Rodar em staging, com banco restaurado/gerado e limites de custo conhecidos:

1. 10 usuários concorrentes;
2. 25;
3. 50;
4. 100;
5. 200;
6. 300;
7. 500;
8. 1.000, quando o plano e o ambiente suportarem com segurança;
9. teste de volume mensal que reproduza 50 mil usuários distintos ao longo da janela de tempo e com rajadas definidas;
10. teste adicional de concorrência maior somente se a necessidade de negócio exigir, com orçamento e autorização explícitos.

Cada etapa só passa se a anterior for compreendida, sem acumular erros silenciosos. O `scripts/locustfile.py` recusa produção e pode ser base para o cenário completo; `scripts/carga_staging.py` que testa `/health` serve apenas como smoke de concorrência simples, não como medidor de capacidade do produto.

## 5. Métricas obrigatórias

### Aplicação/API

- usuários virtuais, rampa, duração, RPS e transações completadas;
- p50/p95/p99 por rota e por fluxo de negócio;
- taxa de erro por status, timeout e retry;
- taxa de login/submissão efetivamente concluída;
- latência de upload/download e tempo de geração/consulta do job;
- CPU, memória, reinício, event loop/threadpool e requests em voo.

### Banco

- conexões disponíveis/ativas/esperando e timeouts de pool;
- tempo de query/lock wait, deadlocks e transações longas;
- top queries por tempo e chamadas;
- CPU/RAM/compute/storage, cache hit se disponível e bloqueios;
- duplicatas e violações de constraint;
- p95 de leitura/gravação por fluxo;
- diferença de schema/migration antes/depois.

### R2, e-mail e IA

- duração, volume de bytes, falha, retry e quota;
- idade do job mais antigo, tamanho da fila e falha permanente;
- custo/latência de IA e frequência de timeout;
- nenhuma dependência externa deve travar operações essenciais indefinidamente.

## 6. SLOs iniciais propostos para o staging

São metas iniciais a confirmar, não medições atuais nem promessas comerciais. A medição pontual de cerca de 689 ms em `GET /health/db`, anotada em `docs/PERFORMANCE.md` (02/10/2026), não demonstra capacidade para 10 mil nem para 50 mil usuários por mês.

- zero acesso cross-tenant em qualquer cenário;
- zero resposta duplicada ou perdida em testes de reenvio/concorrência;
- nenhuma violação de privacidade de CLIMA;
- erro HTTP não esperado abaixo de 1% no cenário nominal depois da rampa, excluindo erro sintético deliberado;
- endpoints core de leitura/escrita com p95 alvo inicial até 800 ms em carga nominal, sem contar processamento assíncrono de IA;
- jobs longos ficam fora do ciclo síncrono e têm prazo/estado de conclusão observável;
- sem esgotamento sustentado do pool ou reinícios de instância durante o teste nominal;
- após a carga, não há aumento de linhas duplicadas, estado inconsistente, fila que não drena nem crescimento inexplicado de recursos.

A equipe pode alterar números após medir a baseline, mas deve escrever por que mudou o SLO e anexar os resultados. Um p95 global esconde rotas lentas; medir separadamente login, submit, lista, painel e arquivos.

## 7. Orçamento de conexões

Calcular a soma máxima provável antes de adicionar workers/replicas:

`conexões_app = réplicas_API × processos_por_réplica × (pool_size + max_overflow)`

Somar conexões de migration job, workers, consoles administrativos e outros serviços. A soma precisa caber com folga no limite do Neon/connection pooler. Em uso de PgBouncer/Neon pooler, testar as limitações do modo transacional e não usar locks de sessão que dependam da mesma conexão server-side persistente.

Não aumentar `pool_size` como tentativa automática de resolver fila; pode apenas transferir o gargalo ou exceder conexões do banco. Primeiro medir pool wait, duração das queries, lock wait e configuração de pooler.

## 8. Caminho de escala recomendado

### Etapa A — eficiência da arquitetura atual

- corrigir schema e migrations;
- agregar queries; matar N+1; paginação;
- manter requests curtas e transações pequenas;
- garantir indexes pelo plano real;
- R2 para todos os arquivos persistentes em production;
- timeouts e retries em integrações;
- jobs duráveis para indexação/relatório/IA;
- métricas e alertas.

### Etapa B — dimensionamento pago, com medição

Aumentar plano/recursos do Render e Neon quando dados de CPU, RAM, pool, compute e p95 indicarem gargalo. Avaliar réplicas stateless de API apenas depois de conferir que rate limit, jobs e estado de sessão não dependem de memória local. Todas as réplicas compartilham o mesmo orçamento de conexão. Separar worker de IA/documentos da API para que pico analítico não bloqueie login e resposta.

### Etapa C — escala adicional se a evidência pedir

Só depois de medir: cache de leitura não sensível e com cache key por tenant/escopo, particionamento de tabelas grandes, read replica, job queue gerenciada ou serviço de busca dedicado. Cada mudança precisa de ADR: problema comprovado, benefício esperado, custo, risco, migração, teste e rollback.

Não introduzir Kubernetes, Kafka, Redis ou microserviços por previsão de MAU. Primeiro medir o monólito modular bem estruturado; adicionar componente externo somente quando o problema exige.

## 9. Backup, restore e continuidade

A meta de 50 mil usuários exige plano de recuperação, não apenas resposta rápida.

- definir RPO (quanto dado recente pode ser perdido) e RTO (tempo máximo de recuperação), aprovado pelo responsável;
- habilitar e compreender retenção/PITR disponível no plano Neon escolhido;
- criar backup/export de dados e objetos de modo coordenado;
- testar restauração em projeto/branch isolado e validar contagens, constraints, documentos e relações;
- documentar como apontar API para banco restaurado e como reverter deploy;
- manter chaves/segredos fora do dump e rotacionar credenciais se houver suspeita de exposição;
- verificar se o R2 precisa de versionamento/retention e como apagar objetos órfãos com segurança;
- não chamar “backup” a um dump sem testar restore.

## 10. Segurança sob carga

O teste de carga também precisa conferir que a segurança não se degrada sob pico:

- rate limit continua entre instâncias;
- `X-Forwarded-For` spoofed não remove limites;
- upload acima do limite retorna rejeição previsível, sem crash;
- respostas simultâneas não duplicam nem permitem replay;
- token expirado/revogado continua recusado;
- usuário A não acessa projetos B com IDs conhecidos;
- K-anonimato permanece sob filtros e resultados parciais;
- falha de LLM/R2/e-mail não expõe informação de outros tenants;
- jobs com retries não duplicam relatório/notificação/índice.

## 11. Modelo de relatório de corrida

Guardar em `docs/performance/` um arquivo por corrida, por exemplo `2026-10-xx-staging-s2-100.md`, com:

- commit, imagem, plano/região, branch de banco e tipo de dados;
- URL de staging sem credenciais;
- cenário, rampa, duração, usuários virtuais, RPS e transações;
- p50/p95/p99 e erros por rota;
- CPU/RAM por serviço, conexão/pool e métricas do Postgres;
- filas/jobs, R2, e-mail e IA quando incluídos;
- problemas observados, query plan e causa provável;
- resultado: PASS/FAIL/INCONCLUSIVO, limites e próxima etapa.

Não publicar host privado, connection string, tokens, PII ou capturas do painel com credenciais.

## 12. Portão de declaração de capacidade

Só publicar “suporta 50 mil usuários ativos/mês” depois que:

- [ ] o cenário de aproximadamente 10 mil usuários/mês tiver sido executado e avaliado primeiro;
- [ ] o cenário de 50 mil mensais tiver sido definido com distribuição e carga por fluxo;
- [ ] a execução ocorrer em infraestrutura paga equivalente à produção prevista;
- [ ] houver pelo menos uma rodada nominal e uma de endurance;
- [ ] p95/p99, erros, CPU/RAM, conexões, fila e integridade estiverem registrados;
- [ ] não houver acesso cross-tenant, resposta duplicada/perdida ou quebra de anonimato;
- [ ] capacidade de backup/restore tiver sido testada;
- [ ] limites, ressalvas e custo estimado estiverem documentados;
- [ ] qualquer afirmação de simultaneidade adicional tiver teste próprio.
