# Gerente Analítico Horizon — desenho futuro

**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Estado:** não implementar. A IA segue desativada.

Não existe versão anterior deste arquivo no repositório. Este texto é o primeiro. Não autoriza rota, prompt, modelo nem gravação de conversa.

## O que o código e os docs já dizem

- `docs/HORIZON_CONTEXTO_IA.md`: Fase 6 suspensa. `configuracoes_projeto.ia_modo` nasce `DESATIVADA` e não há rota para ligar.
- Tabelas `ia_conversas` e `ia_mensagens` aparecem na lista antiga do contexto mestre. Isso não significa que o Gerente está ligado.
- Produto atual é pesquisa, nota e consolidado. O Gerente não copia OKR.

## Portões (todos obrigatórios, nesta ordem)

1. **Banco.** `DATABASE_URL` e `DATABASE_URL_DIRECT` conferidos na tela do Render. Restore de staging combinado. Sem `stamp` e sem reset antes disso.
2. **Segurança.** Suíte de isolamento entre organizações reexecutada e anotada. CLIMA: K=5 e sem autor no agregado, com o teste rodado na data, não só citado.
3. **Produto.** Fluxos da consultora, do funcionário e do órgão vistos de ponta a ponta (`docs/PLANO_FRONTEND_HORIZON.md`).
4. **Carga.** Cenário de 10 mil usuários no mês registrado em staging, sem confundir com simultaneidade (`docs/PLANO_ESCALA_VALIDACAO_50K.md`).

Enquanto um portão estiver pendente, não há tarefa de IA.

## Quando (e só quando) os portões fecharem

O desenho, ainda sem implementar, é: a consultora pergunta sobre agregados que ela já pode ver. A resposta não inclui linha individual de CLIMA abaixo de K=5, não inclui senha, token nem connection string, e não chama modelo de dentro de uma transação de banco. Custo e limite ficam em configuração do projeto, desligados por padrão.

Esse parágrafo é limite de segurança, não especificação pronta para codar.
