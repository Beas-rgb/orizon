# Plano mestre — auditoria incremental

Estado vivo do Orizon. Não apaga o histórico abaixo. Não autoriza reescrita.

Data de abertura: 25/09/2026.

## O que já estava certo (não reescrever)

- CLIMA corta o elo: a resposta vai para um token novo e `participante.token_id` fica nulo. K=5. Arquivo: `app/services/pesquisa/resposta.py`.
- Hierarquia vem de `superior_id`. Ciclo A→A e A→B→A já eram rejeitados. Sem árvore persistida.
- Logout revoga o refresh. Troca de senha revoga sessões. Pool do Render permanece 2.
- Não declarar suporte a 10.000 ou 20.000 simultâneos. A carga atual mede só `/health`.

## Fila por prioridade

| ID | Severidade | Problema | Correção mínima | Estado |
| --- | --- | --- | --- | --- |
| P0-1 | CRÍTICO | Cálculo lia `Resposta.token_id` como id da relação | Tabela `avaliacao_respostas` | corrigido em `544716c` |
| P0-2 | CRÍTICO | Resultado sem checar o usuário | 404 fora de consultora, órgão ou o próprio avaliado | corrigido em `544716c` |
| P0-3 | ALTO | Confirmação da importação confia em `erros` do cliente | Revalidar no backend | corrigido em `fa1819b` |
| P0-4 | ALTO | Superior de outro projeto ganhava perfil | Exigir funcionário deste projeto | corrigido neste documento |
| P1 | MÉDIO | SELECT por relação e `db.get` por nó da árvore | Carga em memória, depois de medir | não agora |
| P2 | INCOMPLETO | Carga real (login → resposta) até 1.000 | Staging/Postgres, fase posterior | não agora |

---

DATA: 25/09/2026
COMMIT: 544716c
OBJETIVO: ligar a nota de desempenho à relação, não ao token da pesquisa.

MUDANÇAS:
- Tabela `avaliacao_respostas` com unique `(relacionamento_id, pergunta_id)`.
- Quem grava é o avaliador da relação. A pergunta tem de ser DESEMPENHO do mesmo projeto.
- O cálculo faz a média por relação e depois por perspectiva, num único agregado SQL.
- Consultora e órgão do projeto leem o resultado. O avaliado lê a própria nota. O resto recebe 404.

PROBLEMA:
- `calcular_resultado_avaliacao` comparava `Resposta.token_id` com o id do relacionamento. Essa coluna é FK de `tokens_resposta`. O teste antigo passava só porque o SQLite não liga FK.

CORREÇÃO:
- Entidade própria. A tabela `respostas` não foi alterada e não foi esvaziada.

ARQUIVOS:
- `app/models/desempenho.py`
- `migrations/versions/0017_avaliacao_resposta.py`
- `app/services/pesquisa/desempenho.py`
- `app/routers/pesquisas.py`
- `tests/test_desempenho.py`

TESTES:
- AUTO 4 e SUPERIOR 5 com pesos 1 e 2 → 4,67, gravado em `avaliacao_respostas` e não em `respostas`.
- Segunda nota na mesma pergunta/relação → 409.
- Outro funcionário e outra consultora → 404. O avaliado vê a própria nota.

MIGRATION:
- `0017_avaliacao_resposta` (upgrade cria, downgrade remove só a tabela nova).

RESULTADO:
- O cálculo não depende mais de token de pesquisa.

RISCOS RESTANTES:
- Geração de relações ainda faz um SELECT por relação (P1).
- Importação ainda confia no cliente (P0-3).
- Superior de fora ainda pode receber perfil (P0-4).
- Carga de 1.000 simultâneos não foi medida.

O QUE NÃO FOI ALTERADO:
- CLIMA, login, pool, importação, árvore e o fluxo de resposta por token. A correção pequena cabia numa tabela nova.

PRÓXIMO PASSO:
- Revalidar a confirmação da importação no backend.

---

DATA: 25/09/2026
COMMIT: fa1819b
OBJETIVO: a confirmação da importação não pode confiar nos erros que o cliente manda.

MUDANÇAS:
- `confirmar_importacao` monta as linhas de novo e chama `validar_linhas`.
- Só entra no banco a linha que a validação do servidor deixou sem erro.

PROBLEMA:
- O backend pulava a linha se `erros` viesse preenchido e gravava o resto sem olhar de novo. Quem apagasse os erros gravava duplicata, superior inexistente ou ciclo.

CORREÇÃO:
- A prévia continua igual. A confirmação repete a mesma validação. Erro inventado pelo cliente não bloqueia linha boa. Erro apagado não libera linha ruim.

ARQUIVOS:
- `app/services/importacao.py`
- `tests/test_importacao.py`

TESTES:
- E-mail duplicado com `erros: []` não cria usuário.
- Linha válida com `erros: ["email inválido"]` é gravada.
- Linha com e-mail inválido continua de fora.

MIGRATION:
- Nenhuma.

RESULTADO:
- O frontend deixa de ser fonte de verdade na confirmação.

RISCOS RESTANTES:
- Superior de outro projeto ainda pode receber perfil (P0-4).
- N+1 na geração de relações e carga real continuam fora.

O QUE NÃO FOI ALTERADO:
- Leitura de CSV/XLSX, limite de 500 linhas e 2 MB, e a prévia. O parser já validava; faltava repetir isso na confirmação.

PRÓXIMO PASSO:
- Superior só pode ser funcionário deste projeto. Testar A→B→C→A e UUID de outro tenant.

---

DATA: 25/09/2026
COMMIT: 0cf1a65
OBJETIVO: o superior da hierarquia tem de ser funcionário deste projeto.

MUDANÇAS:
- `_superior_valido` exige vínculo FUNCIONARIO no projeto e usuário ativo.
- Sem esse vínculo, não cria perfil. A cadeia A→B→C→A continua rejeitada pela subida que já existia.

PROBLEMA:
- Qualquer UUID de usuário virava superior e ganhava um perfil mínimo neste projeto, mesmo vindo de outro órgão.

CORREÇÃO:
- 404, igual ao restante do isolamento. Não há árvore nova no banco.

ARQUIVOS:
- `app/services/estrutura.py`
- `tests/test_estrutura_organizacional.py`

TESTES:
- A→B→C→A responde 422.
- Funcionário do projeto B como superior no projeto A responde 404 e não ganha perfil em A.

MIGRATION:
- Nenhuma.

RESULTADO:
- A hierarquia não atravessa tenant.

RISCOS RESTANTES:
- N+1 na geração de relações e na montagem da árvore (P1). Não medir ainda não autoriza índice às cegas.
- Carga de 1.000 simultâneos no fluxo login → resposta não foi feita. `/health` não conta.
- Importação ainda grava superior por e-mail dentro do próprio arquivo, sem passar por esta função. Isso é o mesmo projeto, não outro tenant.

O QUE NÃO FOI ALTERADO:
- A árvore continua derivada de `superior_id` na leitura. Setor e cargo não montam hierarquia. CLIMA, cálculo e importação não mudaram neste commit.

PRÓXIMO PASSO:
- Medir queries da geração de relações e da árvore antes de trocar o algoritmo. Não subir pool. Não declarar capacidade.

---

DATA: 26/09/2026
COMMIT: 4c34bee
OBJETIVO: reconciliar o plano de 26/09 com o código em `d7b0e8f`. Não reconstruir o que já existe.

MUDANÇAS:
- Este registro. Nenhum comportamento de API neste commit.

PROBLEMA:
- O plano consolidado citava o commit `47d40a9`, 79 testes e 1 falha, e pedia para construir estrutura, importação e motor de avaliação. Isso já está no repositório. A suíte estava em 153 testes verdes.

CORREÇÃO:
- Não refazer Cargo, perfil, CSV, ciclo nem `avaliacao_respostas`.
- Não trocar o `painel()` (já é `GROUP BY`) por `joinedload`.
- Não subir `DB_POOL_SIZE` (segue 2, overflow 0).
- O aviso de publicação já usa `vincular_engine`. O teste citado não é mais o bug aberto.
- Login, primeiro acesso, recuperação, convite e resposta já têm bloqueio de 3 falhas / 5 minutos.
- O teto de importação permanece 500 linhas: um órgão de 200–500 cabe; a linha 501 continua rejeitada.

ARQUIVOS:
- `docs/PLANO_MESTRE_AUDITORIA_GROK_4_7.md`

TESTES:
- Nenhum código novo. A suíte anterior permanece a prova do que já estava pronto.

MIGRATION:
- Nenhuma.

RESULTADO:
- O próximo trabalho é só lista da equipe, participantes, árvore e o rate limit que ainda faltar em upload ou token.

RISCOS RESTANTES:
- `listar_equipe` e participantes ainda fazem `db.get` por pessoa e não paginam.
- A árvore ainda busca usuário, cargo e setor dentro de cada nó.
- Upload da biblioteca e geração de token de resposta ainda serão conferidos no passo do rate limit.
- Carga de 1.000 no fluxo real exige staging. Não existe segundo serviço no Render neste repositório. Não medir em produção.

O QUE NÃO FOI ALTERADO:
- CLIMA, pool, painel, importação, cálculo de desempenho e hierarquia. O plano pedia reconstrução; a evidência diz que isso já funciona.

PRÓXIMO PASSO:
- Paginar `listar_equipe` e trocar o `db.get` em loop por uma leitura `IN`.

---

DATA: 26/09/2026
COMMIT: ffbf75e
OBJETIVO: a lista da equipe não consulta o banco uma pessoa por vez e cabe numa página.

MUDANÇAS:
- `listar_equipe` lê os usuários com `IN` e devolve no máximo 100 itens (`limite` e `deslocamento`).
- A tela de participantes pede `limite=100` e oferece "Carregar mais".

PROBLEMA:
- Cada vínculo fazia `db.get`. Com 500 funcionários o número de queries crescia junto.

CORREÇÃO:
- Uma leitura dos usuários do projeto. A página é corte em memória porque convite pendente e pessoa aceita vêm de tabelas diferentes. O teto de 100 é o mesmo de projetos e pesquisas.

ARQUIVOS:
- `app/services/projeto.py`
- `app/routers/projetos.py`
- `frontend/src/pages/ProjetosPages.tsx`
- `tests/test_listagens_lote.py`

TESTES:
- `limite=1` e a página seguinte não repetem o e-mail.
- Na listagem cheia, a SQL de usuários usa `IN`. Consultas individuais de usuário ficam no máximo 2 (a sessão), não uma por funcionário.

MIGRATION:
- Nenhuma.

RESULTADO:
- A equipe pagina e não faz N+1 de usuário.

RISCOS RESTANTES:
- Participantes da pesquisa e a árvore ainda buscam registro a registro.
- Upload e geração de token ainda serão conferidos.

O QUE NÃO FOI ALTERADO:
- Quem pode ver a equipe (só a consultora dona). O órgão continua sem essa lista. CLIMA, painel e pool não mudaram.

PRÓXIMO PASSO:
- A mesma leitura em lote para participantes (exceto o agregado do CLIMA) e para a árvore, com contagem de queries.

---

DATA: 26/09/2026
COMMIT: 2a294b9
OBJETIVO: participantes e árvore deixam de buscar uma pessoa por nó.

MUDANÇAS:
- Participantes de desempenho: usuários e status numa leitura `IN`, página de até 100. O total continua sendo o da equipe inteira.
- CLIMA segue só com totais. A página não devolve nome.
- A árvore carrega pessoas, cargos e setores uma vez e monta os nós em memória.

PROBLEMA:
- Cada funcionário gerava um `db.get` e, nos participantes, outro `select`. Cada nó da árvore repetia usuário, cargo e setor.

CORREÇÃO:
- Mapas em memória. Sem tabela nova e sem índice novo: 500 linhas cabem numa leitura.

ARQUIVOS:
- `app/services/pesquisa/crud.py`
- `app/routers/pesquisas.py`
- `app/services/estrutura.py`
- `frontend/src/pages/PesquisaEditorPage.tsx`
- `tests/test_listagens_lote.py`

TESTES:
- CLIMA com `limite=1` devolve total 3 e `itens` nulo, sem e-mail no JSON.
- Desempenho devolve uma pessoa na página e total 3. A SQL de usuários usa `IN`.
- Árvore de 4 pessoas usa `IN` e não uma consulta por nó.

MIGRATION:
- Nenhuma.

RESULTADO:
- O número de consultas de usuário não acompanha o tamanho da equipe nessas duas listas.

RISCOS RESTANTES:
- Upload da biblioteca e geração de token de resposta ainda serão conferidos quanto ao `controle_acesso`.
- Carga de 1.000 continua fora: exige staging, pool segue 2/0.

O QUE NÃO FOI ALTERADO:
- O painel agregado, o anonimato do CLIMA, a regra de superior e a paginação da equipe. A geração de relações continua com um select por vínculo: ainda não foi medida em staging, então não foi reescrita.

PRÓXIMO PASSO:
- Se upload ou geração de token não tiver bloqueio, aplicar 3 falhas e 5 minutos de espera. Sucesso não pode contar como falha.

---

DATA: 26/09/2026
COMMIT: 3c16f42
OBJETIVO: upload da biblioteca e geração de token usam o mesmo bloqueio do login.

MUDANÇAS:
- Três falhas seguidas (arquivo inválido, pesquisa ainda em rascunho, quantidade fora do limite) gravam espera de 5 minutos.
- A quarta tentativa responde 429.
- Um envio ou uma geração que dá certo zera o contador. Sucesso não conta como falha — o convite já tinha mostrado que isso trava a consultora no meio do trabalho.

PROBLEMA:
- Essas duas rotas não consultavam `controle_acesso`. Dava para repetir arquivo inválido ou pedido de token sem espera.

CORREÇÃO:
- A chave é `upload:{usuario}` e `tokens:{usuario}`. O mecanismo é o que o login já usa. Não criei outro limitador.

ARQUIVOS:
- `app/services/biblioteca.py`
- `app/services/pesquisa/resposta.py`
- `tests/test_rate_upload_token.py`

TESTES:
- Quatro pedidos de token numa pesquisa em rascunho: os três primeiros 422, o quarto 429.
- Dois uploads inválidos, um texto válido (zera), três inválidos e o seguinte 429.

MIGRATION:
- Nenhuma. A tabela `controle_acesso` já existe.

RESULTADO:
- Abuso nessas rotas espera 5 minutos. Trabalho normal não trava no quarto arquivo válido.

RISCOS RESTANTES:
- Carga de 1.000 no fluxo login → resposta continua sem staging. Pool segue 2 e overflow 0.
- Geração de relações ainda faz um select por vínculo. Não foi reescrita sem medição.
- 10.000 e 50.000 simultâneos não foram medidos e não devem ser afirmados.

O QUE NÃO FOI ALTERADO:
- Login, convite, CLIMA, painel, pool e o teto de 500 linhas na importação. O upload de mídia da pergunta não entrou neste passo: o plano pedia biblioteca e token.

PRÓXIMO PASSO:
- Staging separado de produção, e só então medir o fluxo real. Não subir o pool antes dessa medição.

---

DATA: 26/09/2026
COMMIT: 4b57808
OBJETIVO: o refresh inválido espera 5 minutos, como o login.

MUDANÇAS:
- Três tokens de refresh inválidos no mesmo IP gravam espera.
- A quarta tentativa responde 429.
- Um refresh que dá certo zera o contador daquele IP.

PROBLEMA:
- `refresh` aceitava ou rejeitava o token sem consultar `controle_acesso`. Dava para martelar tokens sem espera.

CORREÇÃO:
- A chave é `refresh:ip:{ip}`. O mecanismo é o do login. Sem biblioteca nova e sem Redis: ainda há um processo só.

ARQUIVOS:
- `app/services/identidade/auth.py`
- `app/routers/auth.py`
- `tests/test_rate_refresh.py`

TESTES:
- Quatro tokens inválidos: 401, 401, 401, 429.
- Dois inválidos, um válido, e mais três inválidos continuam 401.

MIGRATION:
- Nenhuma.

RESULTADO:
- Abuso no refresh espera 5 minutos. Renovar a sessão de verdade não trava o usuário.

RISCOS RESTANTES:
- Carga até 1.000, ZAP e o ensaio de 300 respostas de clima exigem staging. O pool segue 2/0.
- Não existe segundo serviço no Render.

O QUE NÃO FOI ALTERADO:
- Argon2id, pool, CLIMA, slowapi e Redis. Login e upload já tinham o mesmo bloqueio.

PRÓXIMO PASSO:
- Nota 1–5 em radios e mídia só da pergunta visível.

---

DATA: 26/09/2026
COMMIT: 850a9f3
OBJETIVO: a nota de 1 a 5 é um grupo de radios e a mídia não acumula no navegador.

MUDANÇAS:
- `NOTA_5` virou cinco círculos numerados. Cada um é um `radio` com rótulo. O valor enviado continua o inteiro 1–5.
- `NOTA_10` permanece no seletor.
- A resposta baixa só a mídia da pergunta visível e revoga a URL anterior ao trocar.

PROBLEMA:
- A nota era um select. A página baixava a mídia de todas as perguntas de uma vez e segurava os blobs.

CORREÇÃO:
- Só a tela de resposta. O contrato da API não mudou.

ARQUIVOS:
- `frontend/src/pages/ResponderPage.tsx`

TESTES:
- TypeScript do frontend passou. Não há suíte de browser neste repositório.

MIGRATION:
- Nenhuma.

RESULTADO:
- O funcionário escolhe 1–5 pelo teclado. Trocar de pergunta solta a mídia anterior.

RISCOS RESTANTES:
- O editor ainda pede opções separadas por `|`.
- Carga de 1.000 continua sem staging.

O QUE NÃO FOI ALTERADO:
- Backend da resposta, escala 1–10 e o pool.

PRÓXIMO PASSO:
- Lista de opções com adicionar, editar, excluir, subir e descer.

---

DATA: 26/09/2026
COMMIT: 7033f22
OBJETIVO: as opções da pergunta são uma lista, não um texto separado por barra.

MUDANÇAS:
- No editor, adicionar, editar, excluir, subir e descer cada opção.
- Ao salvar a pergunta, a lista vai no campo `opcoes` que o backend já aceita.
- Não há texto fixo do tipo Sim, Não ou Talvez na tela.

PROBLEMA:
- O campo único “separadas por |” escondia a ordem e obrigava a redigitar tudo.

CORREÇÃO:
- Só a tela. O schema da API não mudou. Sim/Não vazio no tipo SIM_NAO continua sendo preenchido pelo backend, não pela tela.

ARQUIVOS:
- `frontend/src/pages/PesquisaEditorPage.tsx`

TESTES:
- TypeScript do frontend passou.

MIGRATION:
- Nenhuma.

RESULTADO:
- A consultora monta as opções sem concatenar texto.

RISCOS RESTANTES:
- Carga de 1.000 e ZAP continuam sem staging. O pool não muda.

O QUE NÃO FOI ALTERADO:
- Contrato de criação e edição da pergunta. Nota 1–10. Pool.

PRÓXIMO PASSO:
- Arquivo Locust que recusa produção e checagem local com Bandit e pip-audit. Sem rodar a matriz e sem ZAP.

---

DATA: 26/09/2026
COMMIT: 8265e49
OBJETIVO: deixar o harness de carga e a checagem estática prontos, sem medir 1.000 e sem ZAP.

MUDANÇAS:
- `scripts/locustfile.py` descreve login, formulário, mídia da pergunta, resposta e nota. Host de produção aborta. Fora do localhost exige `HORIZON_AMBIENTE=staging`.
- `scripts/security_check.py` roda Bandit e pip-audit. Não chama a API.

PROBLEMA:
- Não havia como recusar produção num fluxo completo, e não havia registro da checagem estática.

CORREÇÃO:
- A matriz 10 → 1.000 não foi executada. Não há staging. O pool segue 2/0.

ARQUIVOS:
- `scripts/locustfile.py`
- `scripts/security_check.py`
- `tests/test_carga_harness.py`

TESTES:
- `preparar_alvo` recusa `orizon-api.onrender.com` e aceita `127.0.0.1`.

MIGRATION:
- Nenhuma.

RESULTADO:
- Checagem de 26/09, na máquina local:
  - Bandit: 0 achados altos. Dois médios B310 em `urlopen` de CNPJ e SendGrid. As URLs são montadas no código para HTTPS desses serviços, não vêm do usuário. Aceito. Não trocar o cliente HTTP neste passo.
  - pip-audit: `ecdsa` 0.19.2, PYSEC-2026-1325, dependência transitiva. Sem achado alto no Bandit. Não trocar a biblioteca de criptografia sem um teste que prove a troca. Fica como risco aberto, não como correção.
  - ZAP não rodou.

RISCOS RESTANTES:
- 1.000 simultâneos, espera de pool, CPU/RAM e o ensaio de 300 respostas de clima só existem depois de um staging que não aponta para produção.
- O aviso do `ecdsa` continua aberto.

O QUE NÃO FOI ALTERADO:
- Pool, Argon2id, Redis, slowapi, exportação de clima (não existe e não foi criada) e o Render de produção.

PRÓXIMO PASSO:
- Criar o staging no painel. Só então rodar o Locust, do menor concorrente para o maior, e decidir o pool com esse número.

---

DATA: 26/09/2026
COMMIT: b12f9d7
OBJETIVO: menos consultas no servidor e menos JavaScript na primeira tela.

MUDANÇAS:
- Gerar relações lê as que já existem e só insere a chave nova. A segunda chamada devolve `criados: 0`.
- A importação lê e-mails, vínculos e perfis com `IN`.
- Publicar a pesquisa lê os participantes existentes de uma vez.
- A lista de relações lê os nomes de uma vez.
- As pesquisas do funcionário leem o status de uma vez.
- O navegador carrega login e a entrada de imediato. Trabalho, editor, resposta e painéis só entram quando a rota abre.

PROBLEMA:
- Quinhentas pessoas geravam uma consulta por relação, por linha da planilha e por participante na publicação.
- O navegador baixava o editor e a árvore mesmo em quem só ia entrar.

CORREÇÃO:
- Mapas em memória. Sem migration, sem índice e sem mudar o pool.

ARQUIVOS:
- `app/services/pesquisa/desempenho.py`
- `app/services/pesquisa/crud.py`
- `app/services/importacao.py`
- `app/routers/pesquisas.py`
- `frontend/src/App.tsx`
- `web/app` (build copiado para o Render servir)
- `tests/test_desempenho.py`

TESTES:
- A segunda geração de relações continua com uma linha e agora informa zero criados.
- Importação, desempenho e minhas pesquisas seguiram verdes no recorte.

MIGRATION:
- Nenhuma.

RESULTADO:
- O volume de consultas desses fluxos não acompanha mais o número de pessoas uma a uma.
- A entrada do navegador passou de um arquivo de cerca de 531 KB (gzip 157 KB) para cerca de 291 KB (gzip 91 KB). Trabalho, editor e painéis ficam em arquivos à parte.

RISCOS RESTANTES:
- Carga de 1.000 e ajuste de pool continuam sem staging.
- A tela de resposta continua no arquivo de entrada porque a página de cadastro também a importa.

O QUE NÃO FOI ALTERADO:
- Pool 2/0, plano do Render, plano do Neon, CLIMA, Argon2id e a unique das relações.

PRÓXIMO PASSO:
- Staging, se quiser medir carga.
