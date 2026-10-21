# Relatório de auditoria — Orizon (Horizon)

**Data:** 26 de setembro de 2026  
**Escopo:** código deste repositório no branch `master` (commit `8cd3a9d`), sem alterar a aplicação.  
**O que foi executado de fato:** instalação das dependências, `pytest`, `ruff`, lint e build do frontend, e subida local da API.  
**O que não foi executado:** conexão com o Neon, migrations em Postgres, deploy no Render, varredura de CVE e clique a clique no navegador. Onde a conclusão depende disso, o texto diz “não verificado”.

O repositório chama o produto de **Horizon** no código e de **Orizon** no deploy (`orizon-api`, `orizon-a0u.pages.dev`). É o mesmo software. Este relatório usa **Orizon** para o produto e cita **Horizon** quando o arquivo usa esse nome.

Há auditorias anteriores em `docs/AUDITORIA_2026-09.md` e `docs/PLANO_MESTRE_AUDITORIA_GROK_4_7.md`. Vários buracos daquelas datas já foram fechados (travessia de caminho no SPA, hash de token de pesquisa, logout que invalida o access token, k-anonimato na API de clima, cálculo de desempenho em tabela própria). Este texto não reabre o que o código atual já corrigiu. Descreve o que ainda está aberto.

---

## 1. Resumo executivo

O Orizon **não é um sistema de RH de órgão público**. É um protótipo funcional de **pesquisas aplicadas por uma consultora**: o funcionário responde, vê a própria nota quando o tipo é desempenho, e o órgão vê um painel agregado. Há também um esboço de ciclo de avaliação (auto, superior, subordinado), árvore, importação de equipe e biblioteca de arquivos.

Isso chega perto de uma fatia do [Yespper](https://www.yespper.com/) (avaliação, formulários, importação, painel). Não chega perto de folha, férias, ponto, eSocial ou vida funcional. Um órgão real **não consegue** substituir o sistema de pessoal por este software hoje.

Como protótipo de pesquisa, o backend é mais sério do que o rótulo “vibe coding” sugere: Argon2id, JWT curto amarrado à sessão, isolamento entre projetos testado, 162 testes passando. Como ferramenta para dados reais de servidor público, **ainda não está seguro o bastante**. O anonimato do clima que a tela promete pode ser desfeito no banco. A nota 360 vaza quando só existe um avaliador naquela perspectiva. A trilha de auditoria não serve para prestação de contas.

**Nota geral: 5,0 / 10.**

- Cerca de **6,5 / 10** como demo da consultora (fluxo pesquisa → resposta → painel, com testes).
- Cerca de **3 / 10** como sistema que um órgão público possa usar com dado real de pessoa.

### Os 5 problemas mais graves

1. **Clima não é anônimo para quem lê o banco.** A API esconde o nome, mas a resposta e o participante gravam o mesmo instante. Um `JOIN` por horário reidentifica a pessoa (`app/services/pesquisa/resposta.py`, por volta das linhas 263–307).
2. **A nota 360 de um único avaliador é a nota daquela pessoa.** O resultado devolve a média por perspectiva sem mínimo de respondentes (`app/services/pesquisa/desempenho.py`, função `calcular_resultado_avaliacao`). Com um subordinado, o chefe vê a nota dele. Com um chefe, o servidor vê a nota do chefe.
3. **O limite de tentativas por IP vira limite global no Render.** O processo não confia no IP encaminhado (`Dockerfile`, comando do uvicorn). Refresh e envio de resposta contam o IP do balanceador, que é o mesmo para todo mundo (`app/services/identidade/auth.py`, função `refresh`). Poucas requisições ruins podem bloquear o órgão inteiro. No plano free isso se soma a 512 MB, disco que apaga arquivo local e pool de 2 conexões.
4. **O ciclo de desempenho que a tela descreve não fecha.** O escopo (setor, cargo, manual) é gravado e ignorado na hora de gerar as relações. Não existe transição que tire o ciclo de `RASCUNHO`. A tela fala em “depois de publicado”; o código nunca publica.
5. **Conta pública sem trilha utilizável, e um script que apaga o banco sem trava.** `logs_auditoria` só guarda ação, usuário e hora — sem recurso, sem IP, sem o que mudou. `scripts/reset_manter_ti.py` dá `DELETE` em massa usando o `DATABASE_URL` do ambiente, sem checar se é produção.

---

## 2. Visão geral técnica

### Stack (o que o repositório fixa)

| Camada | Escolha | Onde |
|---|---|---|
| API | Python 3.12, FastAPI, Uvicorn | `pyproject.toml`, `app/main.py` |
| Dados | SQLAlchemy 2, Alembic, Postgres (Neon no desenho) | `app/core/database.py`, `migrations/` |
| Senha | Argon2id via passlib | `app/core/security.py` |
| Sessão | JWT HS256 (15 min) + refresh opaco com hash | `app/core/tokens.py` |
| Arquivo | Cloudflare R2, com fallback em disco local | `app/integrations/arquivos.py` |
| E-mail | SendGrid, senão Mailtrap, senão SMTP, senão arquivo local | `app/integrations/email.py` |
| Tela oficial | React 19, Vite, TypeScript, Tailwind 4 | `frontend/` |
| Tela publicada | build estático servido em `/app` | `web/app/` |
| Teste | pytest + TestClient, SQLite em memória | `tests/conftest.py` |
| Lint Python | ruff (E, F, I, UP) | `pyproject.toml` |
| Lint da tela | oxlint | `frontend/package.json` |

Não há camada `repositories/`. A regra de negócio mora em `app/services/`. Isso é aceitável neste tamanho.

### Estrutura que importa

- `app/routers/` — HTTP fino, na maior parte.
- `app/services/identidade/`, `pesquisa/`, `projeto.py`, `biblioteca.py`, `importacao.py` — domínio.
- `app/core/autorizacao.py` — “este usuário está neste projeto?”. Falha vira 404, para não confirmar que o recurso existe.
- `arquivo/frontend/` — React antigo. O README diz que não é usado. Continua no git.
- `frontend/` — fonte da tela.
- `web/app/` — artefato de build commitado, o que o Docker copia.

Papéis reais: **TI** (autoriza consultora), **CONSULTOR** (cria projeto e pesquisa), **ORGAO** (vê resultado daquele projeto), **FUNCIONARIO** (responde e vê a própria nota de desempenho).

### O que foi rodado neste ambiente (26/09/2026)

Ambiente limpo: Python 3.12.3, Node 22.14.0. Não havia venv nem `node_modules`. O script de setup da imagem não instalou o projeto.

| Comando | Resultado |
|---|---|
| `python3 -m venv` + `pip install -e ".[dev]"` | Instalou. O pacote `python3.12-venv` não vinha na imagem; foi preciso instalar antes. |
| `pytest` sem `PYTHONPATH` (pytest 9.1.1) | **35 erros na coleta.** `ModuleNotFoundError: No module named 'tests'`. O `pyproject.toml` não define `pythonpath`. O README manda só `pytest`. |
| `PYTHONPATH=/workspace pytest` | **162 passed** em ~31 s, 40 arquivos, 3 warnings (httpx/Starlette, `crypt` do passlib, `argon2.__version__`). |
| `ruff check app tests scripts` | **11 erros** (linha longa, import fora de ordem, import não usado, `UP047`). |
| `npm run lint` (oxlint) | Saiu 0. **15 warnings** (estado dentro de `useEffect`, dependência faltando, fast refresh). |
| `tsc -b` e `npm run build` | **Passaram.** Vite 8 gerou o `dist/` em ~300 ms. |
| `uvicorn app.main:app` sem `DATABASE_URL` | Subiu. `GET /health` → 200 `{"status":"ok"}`. `GET /health/db` → 503 `banco indisponível` (mensagem genérica, sem vazar host). `GET /app/` → 200, HTML do SPA. `GET /docs` e `GET /openapi.json` → 200, **sem autenticação**. |

Não apliquei migrations. Não abri o Neon. Não confirmei se o Render de produção está no ar. O `/health/db` 503 daqui é esperado: este ambiente não tem `.env`.

### O que de fato funciona (pelo código e pelos testes)

Os testes cobrem, e passaram nesta máquina:

- login, convite, primeiro acesso, recuperação de senha, bloqueio após 3 erros;
- projeto por CNPJ (a consulta real à BrasilAPI é trocada nos testes);
- pesquisa, publicação, resposta autenticada, mídia com assinatura de bytes;
- clima: a API de participantes não devolve nome; painel com 1 resposta esconde a média;
- desempenho: nota na relação avaliador–avaliado, 404 para quem não é do projeto;
- importação com prévia e confirmação que revalida no servidor;
- IDOR entre projetos respondendo 404 nos fluxos da matriz de segurança.

A tela oficial tem landing, login, cadastro de consultora, projetos, editor de pesquisa (incluindo abas de ciclo), painéis de órgão, funcionário e TI, resposta e biblioteca. Isso está nas rotas de `frontend/src/App.tsx` e nas páginas correspondentes. Eu **não** percorri essas telas no navegador. O build compilou e o HTML de `/app/` foi servido.

### O que não funciona, ou funciona pela metade

- Sem banco configurado, qualquer rota de negócio cai. Isso é esperado.
- E-mail real depende de SendGrid/Mailtrap preenchidos no painel. Sem isso, o convite vai para `data/outbox/`. No Render free, esse disco **não persiste** (documentação do Render, conferida nesta data).
- Arquivo sem R2 vai para `data/biblioteca/` e `data/pesquisas/`. O mesmo disco efêmero apaga o upload no próximo restart.
- Fase 6 (IA) está suspensa de propósito (`ia_modo = DESATIVADA` em `app/services/projeto.py`).
- O rótulo “Cargos e salários” é um **tipo de pesquisa**, não um módulo de remuneração (`ROTULOS` em `app/services/projeto.py`, linhas 41–46).

---

## 3. Bugs e falhas

Gravidade aqui é o efeito se alguém usar o sistema com dado de servidor. “Como corrigir” é a direção, não um patch (o código da aplicação não foi alterado).

### 3.1 Críticas

Nenhuma falha **crítica explorável só pela API**, do tipo “qualquer um lê o `.env`” ou “SQL injection abre o banco”, foi encontrada no código atual. O path traversal do SPA citado na auditoria de 18/09 está fechado em `app/main.py`, função `_arquivo_do_build` (linhas 72–86): o caminho resolvido tem de ficar dentro de `web/app`.

O item abaixo é o mais perto de crítico. Fica em **alta** porque exige leitura do banco (console do Neon, backup, conta TI com SQL), não um endpoint público. Para órgão público, quem administra o banco é parte do modelo de ameaça.

### 3.2 Altas

**A1. Clima: o horário da resposta reidentifica a pessoa**  
Arquivo: `app/services/pesquisa/resposta.py`, linhas 263–307.  
O código cria um token novo e zera `participante.token_id` (linhas 265–270). Isso corta o elo direto, e o teste `test_painel_k_anonimato_n1_suprimido` confere esse corte. No mesmo instante, `agora_` é gravado em `Resposta.respondido_em` e em `participante.respondido_em` (linha 307). Quem tem SQL faz:

```sql
SELECT p.usuario_id
FROM pesquisa_participantes p
JOIN respostas r ON r.respondido_em = p.respondido_em
WHERE p.pesquisa_id = '...';
```

A mensagem da API diz “Sua identidade não é mostrada” (`app/routers/pesquisas.py`, por volta da linha 630). Isso é verdade **na resposta HTTP**. É falso **no banco**. O status `RESPONDIDA` continua ligado ao `usuario_id` (`app/models/pesquisa.py`, classe `PesquisaParticipante`). A lista nominal some na API de clima (`app/services/pesquisa/crud.py`, `listar_participantes_status`, linhas 698–704), mas o vínculo permanece.

Correção: para clima, não gravar `respondido_em` individual, ou gravar só a data (dia), ou um horário arredondado igual para o lote. A resposta anônima não pode compartilhar timestamp único com a linha do participante. Participação (“quantos responderam”) pode existir; o elo com o conteúdo, não. O teste atual precisa ganhar um caso que falhe se os horários forem iguais.

**A2. Resultado 360 mostra a nota de uma pessoa só**  
Arquivo: `app/services/pesquisa/desempenho.py`, `calcular_resultado_avaliacao`, linhas 408–467.  
Consultora, órgão e o próprio avaliado recebem `por_perspectiva`. Não há mínimo de avaliadores. Um subordinado ⇒ a média `SUBORDINADO` é a nota dele. O k-anonimato (`K_ANONIMATO = 5` em `app/services/pesquisa/comum.py`, linha 27) só vale para o painel de **CLIMA**.

Correção: se uma perspectiva tiver menos de K avaliadores, omitir aquela média para quem não é o avaliador da relação. O avaliado não deve ver a perspectiva `SUPERIOR` quando só existe um chefe, se a promessa for sigilo da chefia. Decidir isso por escrito com o órgão antes de codar: em avaliação formal da Lei 8.112 / estatuto, a nota do chefe **não** é anônima. Misturar “clima anônimo” e “avaliação funcional identificada” na mesma tela, sem rótulo, é o erro.

**A3. Limite por IP é global atrás do proxy**  
Arquivos: `Dockerfile` linha 15 (uvicorn sem `--proxy-headers`); `app/routers/auth.py` linha 70 e `app/services/identidade/auth.py` linhas 171–179 (`refresh:ip:{ip}`); `app/services/pesquisa/resposta.py`, `_rate_limit_responder`, linhas 344–379 (também conta `responder:ip:`).  
O Uvicorn, por padrão, usa o IP de quem conectou no processo. No Render, isso é o balanceador, igual para todos os usuários. Três refreshes inválidos bloqueiam o refresh de **todo mundo** por 5 minutos (`login_max_tentativas = 3`). Dez envios de resposta no mesmo IP bloqueiam o envio de todos (`RESPONDER_MAX_TENTATIVAS = 10`).

Não reproduzi isso no Render (não há deploy neste ambiente). A conclusão segue do comando do Docker e do uso de `request.client.host`.

Correção: ligar proxy headers só para os IPs do Render, ler o cliente real com cuidado (não confiar em `X-Forwarded-For` vindo da internet), e não usar um balde único de IP para o plano inteiro. O limite por e-mail no login (linhas 136–141 de `auth.py`) está certo e não tem esse defeito.

**A4. Escopo do ciclo é ignorado; o ciclo nunca sai de rascunho**  
Arquivos: `app/services/pesquisa/desempenho.py`.  
`criar_ciclo` grava `escopo` (linha 103, default `RASCUNHO` na linha 103 do status). `gerar_relacoes` (a partir da linha 180) chama `_funcionarios_do_projeto` e gera AUTO/SUPERIOR/SUBORDINADO para **todos**. `SETOR`, `CARGO` e `MANUAL` não filtram ninguém.  
Busca no código: não há `ciclo.status =` em lugar nenhum. `atualizar_ciclo` e `gerar_relacoes` só aceitam `RASCUNHO`, então o ciclo fica eternamente editável. A tela em `frontend/src/pages/PesquisaEditorPage.tsx` (por volta da linha 1072) fala em travar depois de publicado. Essa trava não existe.  
A rota `POST /projetos/{id}/ciclos` (`app/routers/pesquisas.py`, linhas 640–657) recebe `dict` cru. `inicio_em` e `fim_em` existem no model e na função, e a rota não os repassa. Se `configuracao` vier como objeto JSON em vez de string, `json.loads` em `_validar_configuracao` (linha 51) levanta `TypeError`, que `chamar` não converte: a API responde 500. A tela atual manda string (`JSON.stringify`), então o caminho feliz da UI passa. Um cliente que mande objeto, não.

Correção: filtrar funcionários pelo escopo; criar `publicar_ciclo` que muda o status e bloqueia edição; validar o corpo com Pydantic; aplicar a escala gravada na configuração (hoje `registrar_resposta_avaliacao`, linhas 375–378, aceita qualquer inteiro e qualquer `opcao_id`, sem checar se a opção é da pergunta).

**A5. Script que apaga dados, sem trava de ambiente**  
Arquivo: `scripts/reset_manter_ti.py`, função `main`, linhas 7–81.  
Não há `APP_ENV`, não há confirmação, não há recusa de host de produção. `scripts/carga_staging.py` tem essa recusa. Este script não. Ele faz `DELETE FROM` nas tabelas listadas e apaga usuários que não são TI, na conexão de `DATABASE_URL`.  
A lista está velha: não inclui `ciclos_avaliacao`, `avaliacao_relacionamentos`, `avaliacao_respostas`, `cargos`, `perfis_funcionario`. No Postgres, a foreign key deve fazer a transação inteira falhar (o `begin()` desfaz). Ou seja: o script é perigoso **e** provavelmente quebrado contra o schema atual. Não executei. Não apontar este arquivo para o Neon.

Correção: apagar o script do repositório de aplicação, ou exigir `HORIZON_AMBIENTE=dev` mais um nome de banco que não seja o de produção, no mesmo estilo de `recusar_producao`.

**A6. Trilha de auditoria não presta para órgão**  
Arquivos: `app/models/auditoria.py` linhas 9–20; `app/services/auditoria.py` linhas 10–18.  
Cada linha é `id`, `usuario_id`, `acao`, `criado_em`. Não há id do projeto, da pesquisa, do documento, IP, resultado (sucesso/falha já vai misturado na ação) nem valor anterior. Não há tela para o órgão exportar isso. Para controle interno e para pedido do TCE / corregedoria, “LOGIN” sem dizer de qual conta em qual recurso, além do `usuario_id`, é fraco — e no clima o `usuario_id` é de propósito nulo (`resposta.py`, linhas 326–328), então a linha não diz qual pesquisa.

Correção: colunas `recurso_tipo`, `recurso_id`, `ip` e `resultado`, sem corpo de resposta, sem senha e sem token. Retenção definida. Exportação só para TI, com o próprio acesso auditado.

### 3.3 Médias

**M1. Lista da biblioteca carrega documento de outros órgãos**  
`app/services/biblioteca.py`, `listar`, linhas 132–141. Sem `projeto_id`, a consultora puxa **todo** documento `INTERNA` do banco e filtra em Python com `pode_ver`. A resposta HTTP que li não devolve o arquivo alheio (o filtro existe). O processo, porém, lê metadado de outros tenants. Com volume, vira vazamento de tempo e de memória. Correção: filtrar `consultor_id` ou `projeto_id` no SQL.

**M2. Nome do arquivo entra cru no header**  
`app/routers/biblioteca.py`, linhas 112–119. `Content-Disposition` usa `doc.nome`, que veio de `arquivo.filename` (linha 70) com no máximo 200 caracteres (`biblioteca.py`, serviço, linha 107), sem tirar aspas nem quebra de linha. Não enviei um nome malicioso nesta auditoria. Correção: nome só com caracteres seguros, ou `filename*` no padrão RFC 5987.

**M3. Importação gruda na conta que já existe, em qualquer órgão**  
`app/services/importacao.py`, linhas 332–338 e 398–424. O e-mail é único no sistema (`usuarios.email`). Se o CSV traz um e-mail que já é funcionário de outro órgão, ou consultora, a confirmação reusa essa pessoa e cria vínculo `FUNCIONARIO` neste projeto. Não há checagem de papel. Não reproduzi com dois órgãos reais; o SQL está escrito assim. Correção: recusar e-mail de outro papel; para o mesmo papel em outro órgão, exigir convite explícito em vez de ligar a conta sozinho.

**M4. Erro do Excel volta para o cliente**  
`app/services/importacao.py`, linhas 107–108. `except Exception` embute `str(exc)` na mensagem. O openpyxl pode incluir detalhe interno. Correção: mensagem fixa e o detalhe só no log, sem dado de pessoa.

**M5. ZIP qualquer entra como DOCX**  
`app/integrations/arquivos.py`, `_assinatura_documento`, linhas 85–86. `PK\x03\x04` aceita como Word. Um zip que não é docx passa. O download manda `nosniff` e `attachment`, o que reduz script no navegador. Correção: exigir a estrutura mínima do docx (`word/document.xml`) ou limitar a PDF e imagem.

**M6. Só CLIMA é tratado como anônimo**  
`app/services/pesquisa/comum.py`, linha 28: `TIPOS_ANONIMOS = {"CLIMA"}`. `DIAGNOSTICO_ORGANIZACIONAL`, `PERSONALIZADA` e `CARGOS_SALARIOS` guardam resposta no token da pessoa. Se a consultora usar “cargos e salários” achando que é anônimo, não é. Correção: rótulo explícito na tela e, se o tipo for sensível, o mesmo tratamento do clima.

**M7. Painel de clima com N pequeno ainda diz quantos responderam**  
`app/services/pesquisa/painel.py`, linhas 87–104. Com 1 resposta, `suprimido` é verdadeiro e a média some (o teste cobre isso). O campo `respostas` continua `1`. Num setor de uma pessoa, saber que “1 respondeu” identifica quem participou. A média, não. Correção: abaixo de K, omitir também a contagem fina, ou só mostrar faixa.

**M8. Link de primeiro acesso na mão do TI, mesmo em produção**  
`app/services/identidade/convites.py`, `_expor_link_primeiro_acesso`, linhas 163–166: `para_ti=True` sempre devolve o link. Em produção as outras rotas não devolvem (linha 165). O painel do TI mostra o link (`frontend/src/pages/Paineis.tsx`). Quem rouba a sessão do TI cria a senha da consultora. Correção: em produção, link só no e-mail; na tela, no máximo “reenviar”.

**M9. Rotas da tela não olham o papel**  
`frontend/src/App.tsx`, `RequireAuth`, linhas 64–74. Basta estar logado para abrir `/projetos/novo` ou o editor. A API recusa (os testes de escopo passam). O defeito é de experiência e de superfície: a pessoa vê formulário que não pode usar. Correção: guardar o painel e redirecionar.

**M10. OpenAPI público**  
`app/main.py`, linha 39, `FastAPI(...)` sem desligar `/docs`. Verificado ao subir a API: `/docs` e `/openapi.json` respondem 200 sem login. Correção: `docs_url=None` quando `APP_ENV=production`.

**M11. `pytest` como o README ensina quebra no pytest 9**  
`pyproject.toml` linhas 36–37 não definem `pythonpath`. pytest 9.1.1, nesta máquina, não achou o pacote `tests` (35 erros). Com `PYTHONPATH` apontando para a raiz, 162 passaram. Correção: `pythonpath = ["."]` em `[tool.pytest.ini_options]` e um teto de versão, ou documentar o `PYTHONPATH`.

**M12. Aviso do passlib no Python 3.12, quebra anunciada no 3.13**  
O pytest imprimiu `DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13` vindo de `passlib`. O projeto exige `>=3.12`. No dia em que a imagem for 3.13, o hash de senha pode falhar na importação. Correção: trocar passlib por `argon2-cffi` direto, com `time_cost` e `memory_cost` explícitos (hoje o custo é o default da lib, `app/core/security.py` linhas 11–13).

### 3.4 Baixas

**B1.** `ruff` não está verde (11 achados). São estilo e um import morto em `app/routers/biblioteca.py` (`HTTPException`). Não é vulnerabilidade.  
**B2.** oxlint: warnings de `setState` em `useEffect` (várias páginas, entre elas `AuthContext.tsx` e `PesquisaEditorPage.tsx`). Não quebrou o build.  
**B3.** `ResponderPage.tsx` é importado de forma dinâmica e também estática (`AuthPages.tsx`). O Vite avisou que o chunk separado não acontece.  
**B4.** Dois nomes (Horizon / Orizon) e a pasta `arquivo/frontend/` aumentam a chance de a próxima pessoa editar a tela errada.  
**B5.** `GET /health/db` é público. Só diz se o banco responde. Útil para o Render; também serve de sonda. Aceitável se a mensagem continuar genérica, como está.

### O que foi procurado e não apareceu

- **SQL injection nas rotas.** Consultas passam pelo SQLAlchemy. O único `text()` com interpolação visto é `DELETE FROM {tabela}` no script de reset, com nomes fixos no código, não vindos do usuário. Não é injeção pela API.
- **XSS no React.** Não há `dangerouslySetInnerHTML` em `frontend/src`. O React escapa texto. O HTML do e-mail passa por `html.escape` (`app/integrations/email.py`, `_corpo_para_html`).
- **Senha em claro, JWT sem algoritmo fixo, token de convite em claro.** Senha é Argon2id. O JWT só aceita `HS256` (`app/core/tokens.py`, `ler_access_token`). Convite e refresh guardam SHA-256. Logout marca `revogado_em` e o access token carrega `sid` checado em `app/core/deps.py`.
- **Segredo commitado.** Busca por chaves e senhas no código não achou credencial real. `.env` está no `.gitignore`. `.env.example` tem placeholders. `render.yaml` usa `sync: false` nos segredos. Não abri o histórico inteiro do git em busca de segredo antigo; isso fica como não verificado.
- **CPF, dado de saúde, matrícula.** Não existem colunas disso nos models. O dado pessoal que existe é nome, e-mail, telefone opcional, vínculo de órgão (CNPJ público), resposta de pesquisa e nota de avaliação.

---

## 4. Segurança e LGPD

Órgão público trata dado de servidor sob a LGPD (Lei 13.709/2018) e, em regra, sob a lei de acesso à informação e as normas do tribunal de contas. Opinião de clima e nota de desempenho são dados pessoais. Opinião sobre assédio, saúde mental ou sindicato dentro de uma pesquisa pode ser dado sensível, mesmo sem um campo chamado “saúde”. O código não distingue isso.

### Autenticação

O que está bem feito:

- Argon2id; senha não volta na API.
- Regra de senha no servidor (8 caracteres, maiúscula, número, especial), em `senha_aceita`.
- Login com mensagem única e hash dummy para não revelar se o e-mail existe pelo tempo (`erros.py`, `_hash_dummy`).
- Três erros, cinco minutos de espera, gravado em `controle_acesso`, por e-mail.
- Access de 15 minutos amarrado à sessão. Refresh só como hash, rotação no uso. Troca de senha revoga sessões (há testes de endurecimento; não reli cada assert, a suíte passou).
- Bootstrap de TI desligado quando `APP_ENV` é exatamente `production` (`auth.py`, linhas 112–113). O Docker e o `render.yaml` definem isso. Qualquer outro valor (`Development`, `prod`, vazio) **reabre** `POST /auth/bootstrap` se a tabela estiver vazia. A comparação é string exata.

O que falta para um órgão:

- Segundo fator. Não há.
- Sessão no `sessionStorage` (`frontend/src/lib/api.ts`, linhas 19–21). Qualquer XSS futuro lê o access e o refresh. Cookie `HttpOnly` + `Secure` + `SameSite` reduz isso. Não há XSS óbvio hoje; o depósito do token continua frágil.
- Cabeçalhos de segurança (CSP, `X-Frame-Options`, HSTS) não são definidos pela API no HTML do SPA. HSTS pode estar no Render; não verifiquei o site publicado.

### Autorização

O desenho certo está em `app/core/autorizacao.py`: papel no projeto, soft delete, 404 para não enumerar. TI não ganha papel de projeto (linha 29), então não lista o trabalho dos órgãos. Isso é bom.

Os testes `test_matriz_seguranca_rc.py`, `test_orgao_acesso.py` e `test_paineis_escopo.py` passaram nesta máquina. Eu não montei um segundo ataque manual fora da suíte.

Pontos fracos já citados: biblioteca que lê demais (M1), importação que liga conta global (M3), resultado 360 sem piso (A2), tela que não esconde rota (M9).

`criar_ciclo` ainda exige `consultor.papel == "CONSULTOR"` **e** ser a dona do projeto (`_projeto_da_consultora`). Isso está alinhado ao isolamento.

### Segredos

Não achei segredo no tree atual. O risco operacional é outro: fallback local de e-mail e de arquivo grava token de primeiro acesso e binário em `data/`, pasta ignorada pelo git, porém presente no disco do servidor. No Render free esse disco some; num volume que alguém ligar depois, o token fica em arquivo.

`/dev/diagnostico` exige TI e o comentário diz que não devolve senha nem URL. Não conferi o JSON completo contra um banco populado.

### Validação de entrada

Pydantic cobre login, convite e o grosso das pesquisas. Ciclo e resposta de avaliação usam `dict` (seção A4). CNPJ passa por `normalizar_cnpj` e pela BrasilAPI (`app/integrations/cnpj.py`); o nome do órgão não é o que a tela digita. Não conferi se a BrasilAPI já aceita o CNPJ alfanumérico novo; o código aceita 14 letras/números e delega a consulta. Timeout de 10 s. Sem retry em loop. Bom o bastante.

Upload de documento: tamanho, MIME declarado e assinatura de bytes. Mídia de pergunta: só imagem/vídeo reconhecidos pelo magic number. Isso foi corrigido de propósito e tem teste (`test_seguranca_arquivos.py`, que passou).

### Injeção e XSS

Não encontrei SQL injection nas rotas. Não encontrei XSS armazenado óbvio no React. O risco residual é o header de download (M2) e o ZIP aceito como DOCX (M5).

### Dados pessoais e LGPD — o que o código faz e o que não faz

| Exigência prática | Situação no código |
|---|---|
| Minimizar dado | Não há CPF nem saúde. Há nome, e-mail, telefone, nota e texto livre de pesquisa. Telefone existe no model e o canal SMS não envia (`notificacao.py`, ação `TELEFONE_NAO_HABILITADO`). Coletar telefone sem uso é dado a mais. |
| Base legal / aviso | Nenhuma tela ou texto de privacidade no repositório. Busca por LGPD, consentimento e encarregado só achou a auditoria antiga. |
| Anonimato de clima | Incompleto (A1, M6, M7). |
| Sigilo da avaliação | Incompleto para grupo pequeno (A2). |
| Direitos do titular (acesso, correção, exclusão) | Soft delete em várias tabelas. Não há pedido do titular, exportação da própria ficha, nem rotina de retenção. |
| Registro de operações | Existe, e é pobre (A6). |
| Segurança no trânsito | Depende do HTTPS do Render/Pages. A aplicação não força. Não verificado no domínio publicado. |
| Segurança no repouso | Depende do Neon e do R2. A aplicação não cifra coluna. No plano free do Neon, o histórico de restore é de 6 horas (documentação do Neon consultada em 26/09/2026). |
| Operador e encarregado | Não há modelo disso. A consultora vê painel do órgão cliente. Falta contrato e registro de operador — isso é processo, não está no código, e o código também não ajuda (sem exportar trilha). |
| Vazamento entre órgãos | A API testada responde 404. A importação por e-mail global (M3) e a listagem larga da biblioteca (M1) são os furos de desenho. |

Conclusão de LGPD: **não colocar pesquisa real de clima nem avaliação de servidor neste sistema** até A1, A2 e A6 estarem corrigidos e existir um texto de privacidade revisado por quem responde pelo órgão. Nota de desempenho identificada pode ser lícita (cumprir dever legal de avaliar). Clima “anônimo” que não é anônimo é o caso que gera problema trabalhista e administrativo.

---

## 5. Arquitetura e qualidade

### O que está organizado

A separação router → service → model é real. Autorização foi puxada para um módulo, em vez de três funções que divergiam (isso era achado da auditoria de setembro; o módulo `autorizacao.py` existe e os services de projeto, pesquisa e biblioteca o usam). Migrations têm `downgrade` (17 revisões; a `0001` é baseline vazia de propósito, porque o schema já existia no Neon). Soft delete e `atualizado_em` aparecem nas mutações que li. Testes de autorização são numerosos para o tamanho do projeto. Isso não é o caos típico de um gerador sem revisão.

### Dívida típica de código gerado em sequência

- **Dois frontends e um build commitado.** `arquivo/frontend/` é histórico. `web/app/` é o artefato. `frontend/` é a fonte. O build que rodei gera hashes iguais aos arquivos já em `web/app/` nos nomes que o Vite imprimiu (`index-Bybg964k.js`, `PesquisaEditorPage-BNao13fO.js`, etc.). Não fiz diff byte a byte. O risco é alguém mudar a fonte e esquecer de copiar para `web/app/` antes do Docker, que copia `web/`, não `frontend/dist`.
- **Contratos frouxos** nas rotas de ciclo e de nota de avaliação (`dict` em vez de schema). É o padrão que deixa 500 e nota fora da escala passarem.
- **Testes em SQLite.** `conftest.py` usa `create_all` no SQLite. O próprio plano mestre registra que um teste antigo passava porque o SQLite não aplica foreign key, enquanto o cálculo lia a coluna errada. Aquilo foi corrigido (`avaliacao_respostas`). O método de teste continua podendo esconder o próximo erro de FK ou de tipo do Postgres. A suíte verde **não** prova o Neon.
- **Sem mypy no fluxo.** O `pyproject` cita ruff, e o ruff não está limpo. Tipagem do frontend passou no `tsc`. A do backend não é checada.
- **Arquivos grandes.** `PesquisaEditorPage.tsx` concentra o editor inteiro (a leitura passou de mil linhas). `projeto.py` e `crud.py` de pesquisa continuam longos. Dá para manter, e já dificulta revisão.
- **Nomes e comentários misturam “fase concluída” com comportamento que a tela ainda promete e o service não faz** (publicar ciclo). Documentação otimista é dívida: a próxima sessão de IA vai confiar no README e no RC (`docs/RELEASE_CANDIDATE.md` diz que o ciclo trava pesos; o status não muda).
- **Dependências sem teto superior** (`fastapi>=0.115`, `pytest>=8.3`). Foi o que fez o pytest 9 quebrar a coleta.
- **`python-jose`.** O decode fixa o algoritmo, o que evita o ataque clássico de trocar o algoritmo. A biblioteca está parada no ecossistema. Não rodei scanner de CVE; não vou inventar número de falha. A troca para PyJWT é manutenção, não um furo que eu tenha demonstrado.

Não há pasta de código morto enorme dentro de `app/`. O morto visível é `arquivo/`.

---

## 6. Comparação com o Yespper e com o RH público

Fonte do Yespper, consultada em 26/09/2026:

- Site [https://www.yespper.com/](https://www.yespper.com/): avaliação, comunicação, feedback com gamificação, relatórios, ciclos de avaliação, central de competências, gestão de formulários, objetivos e metas (OKR), feedbacks, controle individual, importação de colaboradores, painel, escolha de competências, feed de notícias. O texto é de marketing. Não entrei numa conta e não vi o produto por dentro.
- Página da empresa no LinkedIn: fundada em 2016, sede em Brasília, plataforma de avaliação de desempenho. A descrição fala em método híbrido (escalas, escolha forçada, fatores e pontos, resultado em quartil). Isso é texto institucional, **não** confirmei na interface.

O Yespper, pelo que o site mostra, é **gestão de desempenho e cultura**, não folha de órgão. O README do Orizon diz o mesmo sobre a etapa atual: não copiar OKR, feedback e feed. A comparação justa é: o Orizon cobre uma parte do Yespper e quase nada do RH estatutário.

“Tem” abaixo significa “existe fluxo usável no código e na tela”, não “pronto para produção”.

| Funcionalidade | Yespper (site / LinkedIn) | Orizon hoje | RH público (8.112, estatuto, eSocial, TCE) |
|---|---|---|---|
| Ciclo de avaliação | Sim, peça central do site | Esboço: cria ciclo, gera relações, grava nota. Escopo ignorado, sem publicar | Avaliação de desempenho periódica, em geral com comissão, recurso e efeito na carreira |
| Formulários / perguntas | Sim | Sim: texto, notas, sim/não, múltipla escolha, checkbox, mídia | Formulário oficial costuma ser fixo em lei ou decreto, não livre |
| Competências | Central de competências | Não | Competências aparecem em alguns planos de cargos; não está no código |
| OKR / metas | Sim, no site | Não, de propósito nesta etapa | Metas de servidor existem em programas de gestão; não são o núcleo da 8.112 |
| Feedback e gamificação | Sim, no site | Não | Feedback contínuo não substitui o processo formal |
| Feed / comunicação | Sim, no site | Não. Há notificação interna e e-mail | Comunicação oficial segue portaria e processo |
| Importar colaboradores | Sim | Sim: CSV/XLSX, prévia, até 500 linhas, cargo, setor, superior | Carga deveria nascer do cadastro funcional (matrícula), não de planilha solta |
| Painel / relatório | Sim, “tempo real” | Sim, agregado, com k-anonimato só no clima | Relatório para gestão e para tribunal (quadros, lotação, despesa) |
| Controle individual | Sim, no site | Nota própria no desempenho; clima não devolve nota individual | Ficha funcional do servidor |
| Portal do servidor | Não aparece como portal de RH no site | Painel mínimo: minhas pesquisas e minha nota | Contracheque, férias, licenças, declarações |
| Clima organizacional | Não é o título do site; pode caber em formulário | Sim, é o fluxo mais fechado | Pesquisa de clima é lícita se o anonimato for real |
| Cargos e salários | Não como folha | Só rótulo de pesquisa | Tabela salarial, enquadramento, progressão, incorporação |
| Folha e 13º | Não | Não | Núcleo do RH público |
| eSocial / DIRF / RAIS / SEFIP | Não | Não | Obrigação de quem paga pessoal |
| Férias, licenças, afastamentos | Não | Não | Direito do servidor e impacto na folha e na frequência |
| Frequência / ponto | Não | Não | Controle de jornada e desconto |
| Progressão e promoção | Não | Não | Tempo, titulação, avaliação, vaga |
| Vida funcional (posse, lotação, vacância) | Não | Organização só dentro do “projeto” da consultora: setor, cargo-texto, superior | Cadastro oficial do vínculo |
| Documentos | Não destacado no site | Biblioteca com visibilidade | Pasta funcional, edital, portaria |
| Relatório TCE / transparência | Não | Não | Quadros de pessoal, remuneração, terceirizados, conforme o tribunal local |
| Multi-órgão com consultora | O site fala em “sua empresa” | Sim: este é o desenho real do produto | Cada órgão é responsável pelo próprio dado; consultor externo é operador |

Lei 8.112/1990 vale para servidor federal. Município e estado usam estatuto próprio, muitas vezes parecido (estágio probatório, avaliação, férias, licenças, processo administrativo). O código não cita lei, prazo de estágio, interstício de progressão nem evento funcional. **Suposição:** a tia usa o Yespper para avaliação e cultura dentro do órgão, ao lado de outro sistema que faz a folha. Não confirmei isso com ela. Se for verdade, o Orizon está mirando o produto certo e ainda não o alcançou. Se a expectativa for “o sistema de RH do órgão”, os dois produtos (Yespper e Orizon) ficam devendo a mesma lista da coluna da direita — e o Orizon ainda deve a coluna do meio.

---

## 7. MVP proposto

MVP aqui é o mínimo para **um órgão pequeno usar de verdade a pesquisa e a avaliação**, com dado de servidor, em plano gratuito, sem fingir que é folha.

Não entra no MVP: folha, eSocial, ponto, férias, licenças, progressão, OKR, feed, gamificação, IA. Colocar isso agora estoura o plano free e dilui o que já existe.

### O piloto precisa conseguir isto

1. Consultora autorizada pelo TI cria um projeto a partir do CNPJ, convida o órgão e a equipe, e o e-mail chega de verdade (SendGrid com domínio, não Gmail no limite de teste).
2. Importa a equipe (nome, e-mail institucional, setor, chefia) sem ligar conta de outro órgão por acidente.
3. Publica uma pesquisa de clima. O funcionário responde logado. **Nem a consultora, nem o órgão, nem um SQL casual no horário conseguem ligar resposta a pessoa.** Abaixo de 5 respostas, o painel não mostra média nem contagem que identifique.
4. Publica um ciclo de desempenho com escopo real (pelo menos “órgão inteiro” e “um setor”). Gera autoavaliação e chefia. A nota do chefe é identificada e rotulada como tal. A nota de subordinados só aparece agregada se houver gente suficiente; senão, some. O ciclo publicado não volta a rascunho.
5. O órgão vê o painel daquele projeto e só daquele. Outro órgão, com o ID na mão, recebe 404.
6. O servidor vê as próprias pendências e a própria nota de desempenho, e não a nota individual do colega.
7. Arquivo de edital fica no R2, não no disco do Render.
8. Toda ação sensível gera auditoria com recurso e IP, sem conteúdo da resposta de clima.
9. Existe texto de privacidade na tela, prazo de retenção, e um jeito de exportar/apagar a conta quando o órgão pedir. Sem isso, o jurídico do órgão não deve autorizar.
10. Backup além das 6 horas do Neon free (dump cifrado fora do git, rotina manual enquanto o plano for grátis) e o script de apagar o banco fora do caminho de produção.

Enquanto 3, 4, 7, 8 e 9 não existirem, o uso honesto é **demonstração com pessoa fictícia**.

---

## 8. Roadmap

Esforço abaixo é tamanho da mudança, não calendário. Pequeno: poucos arquivos, regra localizada. Médio: um fluxo inteiro mais testes de autorização. Grande: módulo novo ou troca de infraestrutura. Os planos free foram lidos na documentação oficial em 26/09/2026.

### Limites dos planos gratuitos (e o risco)

| Serviço | Limite conferido | Efeito no Orizon |
|---|---|---|
| Neon Free | 0,5 GB por projeto; 100 CU-horas/mês; scale-to-zero após 5 min; até 2 CU; 5 GB de tráfego de rede; restore de 6 horas; 10 branches | Estoura storage ou CU-hora e o banco **suspende** até o mês seguinte ou até pagar. Acordar do scale-to-zero deixa a API lenta. 6 horas de restore não é plano de continuidade de órgão. |
| Render Free (web) | 512 MB RAM, 0,1 CPU; 750 horas de instância/mês no workspace; serviço dorme; **disco local não persiste**; sem cartão, estourar banda suspende o serviço | O `render.yaml` pede pool 2 e overflow 0. Cabe demo, não dezenas de pessoas ao mesmo tempo. Arquivo e outbox locais somem no deploy. SMTP bloqueado — o README já diz isso; não retestei a rede do Render. |
| Cloudflare R2 | 10 GB-mês, 1 milhão de operações classe A, 10 milhões classe B, egress grátis no tier free de storage Standard | Cabe PDF e imagem do piloto. Vídeo de 50 MB (limite do código) come o teto rápido. |
| SendGrid | **Não verifiquei** a cota gratuita atual nesta sessão. O README depende dele porque o SMTP do Render free não sai. | Se a cota acabar, convite e “nova resposta” param. O código já tem fallback; em produção o link não volta no JSON (exceto TI). |

Não colocar folha nem ponto neste desenho. Um mês de marcação de ponto de um órgão pequeno já briga com 0,5 GB, com o sono do Render e com a suspensão do Neon.

### Fases

**Fase A — Fechar furo antes de qualquer dado real** (esforço médio, vários pontos localizados)  
A1 anonimato, A2 piso na nota 360, A3 IP do proxy, A5 script de reset, M10 docs desligados em produção, M11 `pythonpath` no pytest, M8 link de TI só por e-mail.  
Teste novo: horário da resposta de clima não iguala o do participante; perspectiva com 1 pessoa não devolve média ao avaliado.

**Fase B — Ciclo que a tela já desenha** (esforço médio)  
Publicar e travar ciclo, honrar escopo, validar nota na escala, Pydantic no lugar do `dict`, e-mail de publicação fora do risco de pool (já existe `BackgroundTasks` na publicação de pesquisa; o ciclo ainda não tem esse fluxo).  
Critério: um setor de 10 pessoas completa auto e chefia, e o órgão vê o número sem ver a redação livre identificada.

**Fase C — Mínimo LGPD do piloto** (esforço médio)  
Auditoria com recurso e IP; não guardar telefone até existir SMS; aviso de privacidade; exportar e apagar conta; R2 obrigatório em produção (recusar subir se `APP_ENV=production` e R2 vazio, para não gravar em disco efêmero); retenção escrita (sugestão de produto: clima agregado guarda X meses, resposta identificada de desempenho segue o prazo do processo de avaliação — o prazo legal quem define é o órgão, não este relatório).

**Fase D — Piloto com um órgão** (esforço médio, depende de gente e de jurídico, não só de código)  
Um CNPJ, dezenas de servidores, não centenas simultâneas. Branch de staging no Neon (o free dá 10 branches) para carga, nunca o banco que teria dado real. Medir pool e CU-hora numa semana de uso. Combinar com o órgão que **não** é sistema de folha. Plano de saída se o Neon suspender: dump e parar o piloto, não “continuar no escuro”.

**Fase E — Depois do MVP, ainda no espírito Yespper** (cada item é esforço médio ou grande)  
Competências, feedback sem gamificação no primeiro corte, metas simples se o órgão pedir. Só depois de A–D estáveis. Feed e gamificação ficam por último: não ajudam o piloto e aumentam dado pessoal.

**Fora de roadmap até haver orçamento de infra e de produto**  
Folha, eSocial, férias, licença, ponto, progressão, portal com contracheque, relatório para TCE. Cada um desses é um sistema. No plano free, além de não caber, o risco de perder o banco no meio da folha é inaceitável.

---

## 9. Próximos 10 passos

1. Parar de usar clima ou avaliação com pessoa real até o elo por horário (A1) e o piso da nota 360 (A2) terem teste que falha se regredirem.  
2. Corrigir o anonimato: resposta de clima sem timestamp único compartilhado com `pesquisa_participantes`.  
3. Omitir média de perspectiva com menos de 5 avaliadores, e escrever na tela se a chefia é identificada.  
4. Ensinar o uvicorn a ver o IP real só atrás do proxy do Render, e revisar o balde `refresh:ip` e `responder:ip`.  
5. Impedir `scripts/reset_manter_ti.py` de rodar contra produção (ou removê-lo). Não executá-lo no Neon.  
6. Publicar ciclo de verdade: status, escopo e escala validados por schema, com teste de setor.  
7. Exigir R2 quando `APP_ENV=production` e desligar `/docs` nesse modo.  
8. Acrescentar `pythonpath` no pytest e deixar o `ruff` verde, para o próximo `pytest` nu não dar 35 erros.  
9. Ampliar `logs_auditoria` com tipo e id do recurso e IP, ainda sem conteúdo de resposta.  
10. Escrever com o órgão, em uma página, o que o piloto é (pesquisa e avaliação) e o que não é (folha, ponto, eSocial), mais o texto de privacidade, antes de convidar servidor de verdade.

---

## Apêndice — como reproduzir o que este relatório mediu

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=. pytest
ruff check app tests scripts
cd frontend && npm install && npm run lint && npm run build
uvicorn app.main:app --host 127.0.0.1 --port 8000
# sem DATABASE_URL: /health 200, /health/db 503, /app/ 200
```

Números desta máquina: pytest 9.1.1, 162 passed com `PYTHONPATH`, 35 erros de coleta sem ele, ruff com 11 erros, oxlint com 15 warnings e exit 0, build Vite ok, API local ok sem banco.
