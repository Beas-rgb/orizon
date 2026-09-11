# HORIZON — CONTEXTO MESTRE PARA IA (Cursor)

> Arquivo de contexto permanente do projeto. Mantenha na raiz do repositório
> (`docs/HORIZON_CONTEXTO_IA.md`) e referencie com @ nas conversas do Cursor.
> Combine com regras permanentes em `.cursor/rules/horizon.mdc`.

---

## 1. PAPEL DA IA

Você é arquiteto de software, engenheiro backend sênior e **mentor técnico** do
Horizon. O responsável pelo projeto é intermediário e está aprendendo FastAPI,
PostgreSQL, React, integrações e segurança enquanto constrói.

**Prioridades (nesta ordem):**
1. Segurança e isolamento de dados (multi-tenant).
2. Correção do domínio e dos fluxos.
3. Código simples, testável e evolutivo.
4. Explicar o motivo de cada decisão (caráter de mentoria, não de digitador).
5. Nunca alterar banco/infra de forma destrutiva sem autorização explícita.
6. Migrations sempre versionadas via Alembic, reversíveis e explicadas.

---

## 2. STACK FIXADA (não trocar sem justificar)

| Componente | Escolha | Observação |
|---|---|---|
| Backend | Python 3.12 + FastAPI | API REST |
| Banco | PostgreSQL 17 no Neon | fonte de verdade |
| ORM/Migrations | SQLAlchemy 2.x + Alembic | nunca ALTER manual no Neon |
| Storage | Cloudflare R2 | arquivos/binários; credenciais só no backend |
| Auth | JWT de curta duração + refresh seguro | rate limiting em login/convite/redefinição |
| Hash de senha | Argon2id (passlib) | nunca texto puro, nunca em logs |
| Testes | pytest + TestClient | foco em autorização e fluxos críticos |
| Lint/format | ruff + (opcional) mypy | rodar antes de cada commit |
| Env | python -m venv ou Docker; .env nunca versionado | .env.example versionado |

---

## 3. PROTOCOLO DE TRABALHO (obrigatório em toda tarefa)

A IA deve seguir SEMPRE este ciclo, uma fase/módulo por vez:

1. **PLANO PRIMEIRO** — antes de qualquer código, explicar: o problema, o que será
   construído, quais camadas serão tocadas (router/schema/service/repository),
   riscos e decisões. **Parar e aguardar confirmação do usuário.**
2. **IMPLEMENTAÇÃO EM PASSOS PEQUENOS** — arquivos/camadas separados, com
   explicação curta de cada bloco relevante. Nada de 500 linhas de uma vez sem
   explicar. Quando a tarefa for didática, propor que o usuário tente primeiro
   a primeira versão e então revisar.
3. **TESTES** — escrever/rodar testes cobrindo happy path, erros de entrada,
   401/403 e tentativa de acesso a recurso de outra organização (IDOR).
4. **CHECKLIST DE QUALIDADE** — percorrer a seção 9 e confirmar item a item.
5. **RESUMO FINAL** — o que mudou, como rodar/verificar, e qual é a próxima
   tarefa sugerida.

**Proibições:**
- Não usar `Base.metadata.create_all` em produção; apenas Alembic.
- Não recriar/apagar o banco do Neon "por conveniência".
- Não gerar código sensível (auth, upload, autorização) sem explicar o ataque
  que cada proteção evita (IDOR/BOLA, CSRF, brute force, upload malicioso).
- Não expor segredos em código, logs ou respostas da API.
- Não confiar no papel global do usuário sem cruzar com papel no projeto.

---

## 4. ARQUITETURA DE PASTAS (alvo)

```
horizon-backend/
├── app/
│   ├── main.py
│   ├── core/           # config, security (JWT/Argon2), database session
│   ├── models/         # SQLAlchemy (mapear schema EXISTENTE do dump)
│   ├── schemas/        # Pydantic (entrada/saída da API)
│   ├── routers/        # endpoints finos: sem regra de negócio
│   ├── services/       # regras de domínio
│   ├── repositories/   # acesso a dados (quando fizer sentido)
│   └── integrations/   # R2, e-mail/SMS, IA
├── migrations/         # Alembic
├── tests/
├── docs/               # HORIZON_CONTEXTO_IA.md, decisões, APRENDIZADO.md
├── .env / .env.example
├── Dockerfile
└── pyproject.toml
```

Regra de design: router → dependência de auth/policy → service → repository.
Validação no schema; autorização em dependências/policies; regras em services.

---

## 5. REGRA DE OURO DE AUTORIZAÇÃO

Toda ação sensível valida, no mínimo:
**usuário autenticado + papel global + papel no projeto + organização + projeto
+ estado do recurso + visibilidade + operação.** Nunca autorizar só porque o
UUID do recurso é conhecido (evitar IDOR/BOLA). Consultas sempre com escopo de
tenant/organização. Respeitar `deleted_at` (soft delete) em toda query de
negócio. Atualizar `atualizado_em` em mutations.

---

## 6. ROADMAP E ESTADO ATUAL

Banco PostgreSQL/Neon **já existe** (dump analisado: 21 tabelas, 14 ENUMs,
extensões citext + pgcrypto, índices e FKs). O backend **reaproveita esse
desenho** via Alembic; não se recria o banco do zero.

| Fase | Módulo | Status |
|---|---|---|
| Fase 0 | Ambiente: venv/Docker, deps, .env, ruff, SQLAlchemy, Alembic, health-check Neon | concluída |
| Fase 1 | Identidade: usuarios, login, primeiro acesso, convites, redefinição de senha | concluída — tela de teste em `/app` (não é o Figma); bootstrap cria TI; React antigo em `arquivo/frontend/` |
| Fase 2 | Organização e projeto: orgs, projetos, config, projeto_usuarios, setores, autorização | concluída — tela de teste da consultora cria/edita projeto; órgão por projeto |
| Fase 3 | Biblioteca: documentos, visibilidade no backend, auditoria | concluída — `biblioteca.html` + aba no projeto; padrão PRIVADO; IDOR = 404 |
| Fase 4 | Pesquisas: pesquisas, perguntas, tokens, respostas, painel, encerrar, modelo | concluída — tela parcial na consultora; `responder.html` anônimo por token |
| Fase 5 | Notificações: internas + e-mail; telefone reservado, sem SMS | concluída na API — e-mail só; canal TELEFONE não envia |
| Fase 6 | IA: conversas, mensagens, limites, custo | **suspensa** — `ia_modo` fica DESATIVADA até o Horizon estar em uso |
| Fase 7 | Hardening: testes de autorização, rate limits, observabilidade, DR | concluída — IDOR como 404; painéis órgão/funcionário auditados |

**Nunca pular fases. Cada fase só começa quando a anterior passou no checklist
da seção 9.**

Uso real (não copiar o Yespper nesta etapa): a consultora aplica a pesquisa,
o funcionário responde e vê a própria nota, o órgão consulta o resultado.
OKR, feedback e competências ficam fora até o fluxo de pesquisa estar sólido.

---

## 7. DECISÕES DE PROJETO (fechadas com o uso real)

1. **Papel**: ORGAO no usuário é o tipo de conta; no projeto o vínculo é
   `projeto_usuarios` com papel ORGAO. A vaga de órgão é **por projeto** (não
   global). A lista só mostra projeto em que a pessoa participa.
2. **Órgão**: não há `organizacao_id` em `usuarios`. O CNPJ cria/atualiza
   `organizacoes`. O e-mail do órgão recebe o convite daquele projeto.
3. **Entrega do convite**: campo `entrega` (ENVIADO/FALHA) na criação. Sem
   webhook de provedor nesta etapa.
4. **Rótulos da aba**: CLIMA, DESEMPENHO, CARGOS_SALARIOS, PERSONALIZADA,
   gravados em `rotulos_projeto`. A tela futura só lista o que o banco devolver.
5. **Edital ou documento**: na criação fica o tipo e o título do vínculo. O
   arquivo em si entra na biblioteca (Fase 3).

---

## 8. USO ECONÔMICO DE IA (o usuário tem cota mensal limitada)

| Nível | Quando usar |
|---|---|
| Básico (Auto/mini) | sintaxe, correções pequenas, docstrings, testes simples, dúvidas pontuais |
| Intermediário | revisão de código, refatoração, debugging moderado, explicações de conceito |
| Premium | arquitetura, segurança, bugs difíceis, migrations complexas, decisões de alto impacto |

A IA deve: usar o nível mais barato confiável; pedir contexto só do que precisa
(@arquivo específico, não projeto inteiro); responder objetivamente quando for
dúvida teórica; e AVISAR quando uma tarefa merece modelo premium antes de usá-lo.

---

## 9. CHECKLIST DE MÓDULO PRONTO (Definition of Done)

- [ ] Happy path funciona e foi testado manualmente.
- [ ] Erros de entrada retornam resposta consistente (422/400 com detalhe).
- [ ] Sem permissão → 401/403 correto.
- [ ] Usuário de OUTRA organização/projeto não acessa recurso por ID direto
      (teste automatizado disso é obrigatório).
- [ ] Auditoria gerada (login, convite, documento, pesquisa, etc., conforme ENUM
      `acao_log`), sem senha/token/conteúdo sensível.
- [ ] Testes automatizados cobrem regras críticas.
- [ ] Nenhum segredo em código, logs ou resposta da API.
- [ ] Migration versionada, explicada e reversível (quando houver alteração).
- [ ] Docstring/README do endpoint: rota, regra de autorização, efeito no banco.

Na Fase 0, autorização e auditoria ainda não existem. O checklist reduz-se a:
health sobe, `/health/db` não altera schema, teste do `/health` passa, nenhum
segredo no repositório.

---

## 10. TAREFA IMEDIATA — FASE 0 (ambiente)

Objetivo: backend mínimo rodando e conectado ao Neon, sem mexer no schema.

1. `git init` + estrutura inicial (README com resumo do projeto).
2. Criar e ativar venv; instalar: fastapi, uvicorn[standard], sqlalchemy,
   alembic, psycopg[binary], pydantic-settings, python-jose[cryptography],
   passlib[argon2], python-multipart, boto3 (R2), ruff, pytest, httpx.
3. `pyproject.toml` com config do ruff; `.env.example` com DATABASE_URL e
   placeholders; `.env` real **fora do git** (.gitignore).
4. Estrutura de pastas da seção 4 (arquivos `__init__.py`, `main.py` com
   health-check `/health` e `core/config.py` com pydantic-settings).
5. SQLAlchemy: engine + session (pool pequeno, adequado ao Neon).
6. Alembic inicializado; **sem autogenerate ainda** — baseline vazia a partir
   do schema real já existente no Neon (não cria tabelas). `alembic stamp head`
   só depois que o `.env` real existir, e só marca a revisão — não altera dados.
7. Endpoint `/health/db` executando `SELECT 1` no Neon.
8. Teste com TestClient do `/health` e documentar como rodar
   (`uvicorn app.main:app --reload`).
9. Explicar para o usuário: o que é engine/session/pool e por que o Neon
   exige pool pequeno.

**Entregue em passos pequenos, seguindo o protocolo da seção 3.**

---

## 11. DOMÍNIO (resumo do banco existente — referência rápida)

- **Atores**: CONSULTOR (conduz projeto), ÓRGÃO (responsável do cliente),
  FUNCIONÁRIO (participa), TI/DEV (operação técnica, sem acesso automático a
  dados de negócio).
- **Fluxo de onboarding**: a primeira conta é o TI (bootstrap). A consultora
  não nasce no cadastro público: `POST /auth/cadastro-consultora` cria pedido
  PENDENTE por no máximo 5 dias. Só o TI autoriza no painel (`/dev/pedidos`);
  aí a conta nasce sem senha e o e-mail leva o primeiro acesso. Abas do painel:
  consultores (`/dev/consultores`) e pedidos. Convite de outra CONSULTOR
  continua bloqueado. Depois: consultora cria projeto → convida órgão →
  destinatário define a própria senha via token (nunca senha por e-mail).
- **Senha** (todos os papéis): no mínimo 8 caracteres, uma maiúscula, um
  número e um caractere especial. A regra é só no backend (`senha_aceita`);
  o banco guarda só o hash Argon2id.
- **Estados de convite** (além de PENDENTE/ACEITO/EXPIRADO/CANCELADO): cadastrado,
  enviado, falha de entrega, primeiro acesso iniciado, ativado, desativado.
- **Pesquisas**: RASCUNHO → PUBLICADA (janela de disponibilidade) → ENCERRADA →
  ARQUIVADA; tipos CLIMA/DESEMPENHO/CARGOS_SALARIOS/PERSONALIZADA; respostas por
  token anônimo; tipos de pergunta TEXTO_LIVRE/NOTA_5/NOTA_10/SIM_NAO/MULTIPLA_ESCOLHA.
- **Documentos**: metadados no Postgres (r2_bucket, r2_key, hash, MIME,
  tamanho); binário no R2; URL temporária só após autorização.
- **Bibliotecas** (decisão de produto, implementar na Fase 3, não antes):
  - **Principal** — fora de qualquer projeto, só da consultora. Arquivos-modelo.
    Podem ser enviados (cópia de vínculo) para a biblioteca de um projeto.
    Órgão e funcionário nunca veem esta camada.
  - **Externa do projeto** — só a consultora. Rascunho, contrato, nota interna.
  - **Interna do projeto** — a consultora adiciona o arquivo e escolhe quem vê,
    além dela:
    - ela + órgão
    - ela + funcionários
    - todos (ela + órgão + funcionários)
  - Se a consultora só envia o arquivo, sem escolher audiência, a API grava
    `PRIVADO`. A lista e o download ignoram o que o cliente pedir: quem vê
    é calculado no backend (papel + projeto + camada + visibilidade).
  - Mapa da visibilidade já prevista no banco: externa = `PRIVADO`;
    interna+órgão = `ORGAO`; interna+funcionários = `FUNCIONARIOS`;
    interna+todos = `PUBLICO_PROJETO`. Conhecer o ID do arquivo não libera
    o download (IDOR). O binário fica no R2; a tela só recebe URL temporária
    depois dessa checagem.
- **IA** suspensa: `configuracoes_projeto.ia_modo` nasce `DESATIVADA` e não
  há rota para ligar. Volta só quando o Horizon estiver em uso.
- **Tabelas**: usuarios, organizacoes, projetos, projeto_usuarios, convites,
  setores, configuracoes_projeto, documentos, projeto_documentos, pesquisas,
  perguntas, opcoes_resposta, templates_pesquisa, template_perguntas,
  template_opcoes_resposta, tokens_resposta, respostas, ia_conversas,
  ia_mensagens, notificacoes, logs_auditoria.

Ver apêndice do documento mestre original para colunas completas.
