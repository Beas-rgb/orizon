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
COMMIT: (este commit)
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
