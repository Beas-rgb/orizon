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
| P0-1 | CRÍTICO | Cálculo lia `Resposta.token_id` como id da relação | Tabela `avaliacao_respostas` | corrigido neste documento |
| P0-2 | CRÍTICO | Resultado sem checar o usuário | 404 fora de consultora, órgão ou o próprio avaliado | corrigido neste documento |
| P0-3 | ALTO | Confirmação da importação confia em `erros` do cliente | Revalidar no backend | pendente |
| P0-4 | ALTO | Superior de outro projeto ganhava perfil | Exigir funcionário deste projeto | pendente |
| P1 | MÉDIO | SELECT por relação e `db.get` por nó da árvore | Carga em memória, depois de medir | não agora |
| P2 | INCOMPLETO | Carga real (login → resposta) até 1.000 | Staging/Postgres, fase posterior | não agora |

---

DATA: 25/09/2026
COMMIT: (preenchido no commit desta correção)
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
