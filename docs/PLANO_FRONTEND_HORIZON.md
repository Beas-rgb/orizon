# Horizon — Plano de evolução do frontend e da experiência da consultora

**Versão:** 1.1\
**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Relatório de Passo 0:** [`RELATORIO_PASSO_0_2026-10-08.md`](RELATORIO_PASSO_0_2026-10-08.md). Esse arquivo é a nota curta do baseline. Não traz o procedimento de reconciliação do banco nem resultado de teste E2E.
**Stack atual:** React 19, TypeScript, Vite, Tailwind CSS 4, React Router, Vitest, Oxlint.

## 1. Estado observado

O CI inclui build/lint/test do frontend, mas a suíte não foi executada durante o Passo 0 e não há evidência apresentada de cobertura E2E de navegador para o produto completo. Adicionar E2E após a reconciliação do banco e o fechamento da segurança crítica; testes devem usar apenas contas e dados sintéticos.

O front principal está em `frontend/` e tem build para Cloudflare Pages (`npm run build:pages`) e publicação da SPA no fallback `/app` (`npm run publish:app`). `App.tsx` usa lazy loading para diversas páginas; `AuthContext.tsx` preserva estado em falhas transitórias e tenta reconectar; `api.ts` tem timeout, tratamento de erro e refresh. Há páginas para login, primeiro acesso, recuperação, projetos, pesquisa, painéis, biblioteca indiretamente ligada aos trabalhos e laboratório.

A dashboard da consultora (`ConsultoraDashboard.tsx` + `InicioConsultoraNovo.tsx`) busca `/projetos` e deriva contagens de status dos projetos recebidos. É uma base honesta de navegação, mas ainda não materializa o “Gerente Horizon” que analisa vários conjuntos de dados e explica evidências. `SmartBriefing.tsx` é um componente de apresentação com prioridades/indicadores recebidos como props; seu nome não demonstra a existência de um backend analítico conectado.

## 2. Experiência-alvo: começar pelo trabalho, não pelo menu de módulos

O modelo mental central é **Trabalho**, que representa o serviço/projeto em uma organização cliente. A consultora não deve precisar entender a arquitetura técnica para conduzir a tarefa.

```text
Início da consultora
  ├─ trabalhos ativos e próximos marcos
  ├─ pendências e alertas fundamentados em dados
  ├─ criar/retomar trabalho
  └─ Gerente Horizon: “o que merece atenção?”

Trabalho
  ├─ Visão geral
  ├─ Organização e estrutura
  ├─ Pessoas
  ├─ Pesquisas
  ├─ Avaliações
  ├─ Documentos e biblioteca
  ├─ Resultados e evidências
  ├─ Plano de ação
  ├─ Relatórios/entregáveis
  └─ Histórico/auditoria
```

Módulos futuros podem aparecer quando existirem e estiverem habilitados, sem criar telas falsas ou botões que não concluem a tarefa.

## 3. Fluxos primários por papel

### 3.1 Consultora

- abrir a visão de portfólio com dados reais de trabalhos;
- criar trabalho/organização e conferir vínculo/tipo;
- importar CSV/XLSX, mapear campos, revisar prévia e conflitos;
- ver e ajustar setores, cargos e hierarquia;
- criar, configurar, publicar, monitorar e encerrar pesquisa/ciclo;
- consultar resultados com a amostra/limitações visíveis;
- pesquisar documentos e gerar entregáveis;
- acompanhar plano de ação e pendências;
- abrir o Gerente Horizon e inspecionar achados/citações;
- exportar somente resultados permitidos.

### 3.2 Órgão

- acompanhar fases, prazos e entregas de seu trabalho;
- abrir documentos explicitamente compartilhados;
- consultar resultados apenas com agregação e visibilidade permitidas;
- não receber lista nominal de participantes de CLIMA;
- não enxergar rascunhos privados nem dados de outro órgão.

### 3.3 Funcionário

- entrar com link/autenticação apropriada e poucos passos;
- completar formulário em celular, com teclado e leitor de tela;
- ver confirmação clara e evitar duplicidade por refresh/duplo clique;
- consultar somente a própria avaliação/nota quando a modalidade permite;
- não acessar organograma/dados individuais alheios ou painéis da consultora.

### 3.4 TI/operador

- gerir credenciais e ambiente sem acesso automático a todos os resultados de negócio;
- usar ambiente e dataset sintéticos para diagnóstico;
- visualizar logs sanitizados, estado de serviços e falhas sem ver senha, tokens ou conteúdo de pesquisa desnecessário;
- não ter ferramentas de “limpeza de produção” acessíveis como rotina normal.

## 4. O que falta para a experiência “smartphone top de linha”

**Ordem obrigatória:** primeiro segurança e integridade do dado; depois jornada operacional e acabamento visual. Não fazer redesign amplo enquanto existir P0 de banco, autorização, anonimato ou reset destrutivo.

### P0 — clareza e segurança do dado

- assegurar que tela nenhuma trate proteção do frontend como autorização;
- remover todos os indicadores fictícios e estados simulados que pareçam resultados reais;
- refletir supressão do K-anonimato nas telas, filtros, exportações e relatórios;
- erros não podem vazar stack trace, token, configuração ou existência de recurso alheio;
- downloads de arquivo sempre passam por autorização do backend;
- tela de CLIMA não pode mostrar quem respondeu/em andamento;
- diferenciar “sem dados”, “carregando”, “falha de rede”, “sem permissão” e “resultado suprimido”.

### P1 — jornada operacional

- checklist de preparação do trabalho;
- estados visíveis de importação (lido, mapeado, inválido, aguardando confirmação, concluído, parcialmente concluído);
- prévia compreensível para linhas inválidas e conflitos de identidade;
- status de ciclo, datas e próximos passos;
- links de notificações levam diretamente à tarefa;
- pesquisa de conteúdo em documentos respeita permissão e indica a fonte;
- relatórios mostram período, amostra, método e versão;
- ações longas exibem status de job e permitem reabrir a tela sem perder progresso.

### P2 — Gerente Horizon

- resumo da situação do trabalho baseado em indicadores reais;
- achados ordenados por relevância com evidências clicáveis;
- indicação de hipótese versus fato calculado;
- área “o que ainda não sabemos”;
- recomendação de próxima investigação, com aprovação humana;
- histórico de análises e comparação entre ciclos;
- feedback “útil / incorreto / evidência fraca” ligado ao achado e versão do modelo, sem treinar automaticamente com PII.

## 5. Organização do código: evoluir incrementalmente

Estrutura alvo, preservando componentes que funcionam:

```text
frontend/src/
  app/              # rotas, providers e composição
  auth/             # identidade e sessão
  components/        # elementos compartilhados
  ui/               # primitivas acessíveis e estados
  features/
    trabalhos/
    estrutura/
    pesquisas/
    avaliacoes/
    biblioteca/
    resultados/
    gerente/
    relatorios/
  lib/
    api/             # cliente HTTP e contratos
    telemetry/       # métricas sanitizadas quando necessário
  pages/             # composição de features, não regra de negócio
  styles/
```

Não mover todos os arquivos em um único refactor. Uma funcionalidade nova começa com sua pasta; arquivos antigos só migram quando houver mudança funcional aprovada. Páginas coordenam; componentes apresentam; estado de servidor deve ter um dono claro; contratos TypeScript precisam acompanhar mudanças de API.

## 6. Contrato com a API

- Backend é a fonte da verdade para permissões, cálculos e transições.
- Tipos de resposta não devem usar `any` nas fronteiras principais.
- Não reproduzir regra de negócio em React para “acelerar” UI; o front pode esconder/mostrar controles por UX, mas a API verifica novamente.
- Normalizar `ApiErro`/erros de validação sem perder `status`, `retryAfter` e `request_id`.
- Não repetir uma mutação automaticamente sem saber se é idempotente; para POST de resposta/importação/publicação usar idempotência do servidor e feedback de retry seguro.
- Não colocar texto completo de documento ou resposta pessoal em analytics de frontend.
- Timeout/abort deve distinguir cancelamento de operação e perda de conexão; mensagens precisam indicar se o servidor pode ter recebido a ação.

## 7. Sessão no browser

No snapshot analisado, tokens são guardados em `sessionStorage`, portanto o JavaScript da mesma origem pode acessá-los. Isso não significa automaticamente que exista XSS, mas eleva o impacto de qualquer injeção executável.

Ações:

1. aplicar CSP alinhada ao build e à topologia Cloudflare/API;
2. manter conteúdo do usuário escapado; não usar `dangerouslySetInnerHTML` para documentos/respostas;
3. evitar scripts de terceiros sem análise;
4. checar dependências e integridade de build;
5. não imprimir token no console, URL pública, query string de analytics ou Sentry;
6. planejar avaliação de cookie HttpOnly/Secure/SameSite ou BFF se justificável, incluindo CSRF/CORS e links de primeiro acesso. Não alternar estratégia de auth sem rollout e testes coordenados.

## 8. Responsividade e acessibilidade

Testar no mínimo larguras móveis comuns e desktop, zoom 200%, teclado-only, foco visível, labels, ordem de heading, contraste e mensagens de erro associadas aos campos. O fluxo de resposta do funcionário é prioridade máxima para mobile; no desktop a consultora precisa suportar tabelas e organogramas grandes sem controles inacessíveis.

Regras práticas:

- toque mínimo confortável em ações primárias;
- nenhum fluxo essencial depende de hover;
- tabela grande tem alternativa responsiva ou paginação;
- foco retorna à ação que abriu modal/drawer;
- erro não depende só de cor/ícone;
- formulário indica obrigatoriedade, progresso, erro recuperável e envio concluído;
- evitar texto truncado como única forma de expor cargo/órgão ou evidência.

## 9. Desempenho do front

- manter lazy loading de rotas e evitar carregar biblioteca/IA no login;
- definir budget de tamanho do bundle principal e dos chunks;
- usar cache/ETag para assets; não cachear respostas pessoais compartilhadas;
- paginação do backend para listas longas;
- virtualização só quando medição demonstrar necessidade;
- upload/download não manter múltiplos arquivos grandes em Blob na memória;
- qualquer busca com LLM retorna job/estado assíncrono quando puder ultrapassar orçamento de UI;
- monitorar erros e Web Vitals sem gravar conteúdo privado.

## 10. Testes frontend necessários

A suíte atual inclui Vitest para helpers/estado, mas as fontes lidas não mostram uma suite E2E de browser cobrindo o produto completo. Adicionar Playwright ou ferramenta equivalente depois de confirmar o pipeline de CI, começando com casos de alto risco:

1. login, refresh e logout;
2. falha temporária da API não apaga sessão válida sem motivo;
3. criar trabalho e importar dataset sintético;
4. publicar pesquisa e responder no mobile;
5. duplo submit não duplica resposta;
6. CLIMA com N abaixo do K oculta dados sensíveis;
7. usuário de outro projeto tentando URL/ID manualmente não vê dados;
8. download de documento respeita visibilidade;
9. página que recebe erro 401/404/429/5xx mostra estado correto e mantém caminho de recuperação;
10. dashboard não apresenta métrica fictícia como dado real;
11. job longo persiste visualmente entre navegações;
12. acessibilidade automática nas telas de login, responder e painel principal.

Datasets e contas devem ser sintéticos, sem copiar nomes, e-mails ou respostas de órgãos reais.

## 11. Definition of Done de cada tela

- [ ] Estado loading, vazio, sucesso, parcial, erro e retry definidos.
- [ ] Todos os dados exibidos vêm de API ou fixture claramente rotulada como demonstração.
- [ ] Sem autorização crítica no cliente.
- [ ] Responsividade e teclado validados.
- [ ] Ações com efeitos no servidor têm feedback, tratamento de repetição e falha.
- [ ] A tela não mostra dados de outro tenant ou status identificável de CLIMA.
- [ ] Tipos de request/response alinhados à API.
- [ ] Vitest/E2E relevante e build TypeScript passam.
