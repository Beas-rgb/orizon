# Modelo de dados

> Nota 08/10/2026: a frase abaixo que limita índice a 0018/0019 descreve o momento em que esses índices nasceram. O git já tem `0020_lab`. Os índices quentes desta página continuam válidos como desenho. Não é inventário do banco do Render. Ver `docs/AUDITORIA_BANCO_SEGURANCA_2026-10.md`.

As migrations 0001 a 0017 não são editadas. Índice novo entra em 0018 ou 0019.

## Índices quentes

- `ix_projeto_usuarios_usuario_id`: a autorização de cada request do projeto procura o vínculo pelo usuário.
- `ix_sessoes_usuario_aberta`: revogar sessões filtra `usuario_id` e `revogado_em` nulo. O índice é parcial para ocupar pouco espaço.
- `ix_setores_projeto_id`: a estrutura lista setores do projeto.
- `ix_perfis_funcionario_superior_vivo`: a rota de filhos filtra `superior_id` e `deleted_at` nulo. Antes disso a árvore era montada em Python e o índice não se justificava.

Não indexamos chave estrangeira rara só por existir. Convite, documento e log de auditoria ficam sem índice extra.

## Unique

`usuarios.email` e `organizacoes.cnpj` são unique. O unique já cria o índice. O model não pede um segundo `index=True`.

## Retenção

Sessão revogada ou vencida há mais de 2 dias sai. Controle de acesso sem bloqueio vigente sai depois de 1 dia. Token de senha usado ou vencido sai depois de 7 dias. Entrega de mensagem sai depois de 90 dias. Notificação lida sai depois de 180 dias. Auditoria sai depois de `RETENCAO_AUDITORIA_DIAS`, padrão 365.
