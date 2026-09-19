# Orizon — regra para adicionar features

Documento oficial de como **qualquer funcionalidade nova** entra no
projeto. Vale para backend, frontend, migrations e integrações.

Referências: `docs/HORIZON_CONTEXTO_IA.md`, `.cursor/rules/horizon.mdc`,
`docs/AUDITORIA_2026-09.md`.

---

## 1. Princípio

Uma feature só entra se for:

1. **Leve** — resolve um propósito claro, sem arrastar sistemas extras
   (Kafka, microserviços, reescrita completa) quando o núcleo atual basta.
2. **Segura** — autenticação, autorização por escopo, IDOR → 404,
   sem segredos em código/logs/respostas.
3. **Sem conflito** — não quebra fluxos prontos (login, projeto, pesquisa,
   resposta, painel, biblioteca) nem divergir de regras já fechadas
   (ex.: clima anônimo, bootstrap desligado em produção).
4. **Com propósito cumprido** — o comportamento esperado está definido
   antes do código e é comprovado depois.
5. **Alinhada à regra de negócio** — consultora aplica pesquisa;
   funcionário responde e vê a própria nota (quando o tipo devolver);
   órgão vê consolidado. Nesta etapa: **sem** OKR, feed social ou
   clone de RH completo.

Código existente **não** significa comportamento comprovado.

---

## 2. Ciclo obrigatório (nesta ordem)

```text
PROPÓSITO / REGRA DE NEGÓCIO
        ↓
PLANO (camadas, riscos, o que NÃO fazer)
        ↓
confirmação do responsável
        ↓
IMPLEMENTAÇÃO LEVE (passos pequenos)
        ↓
TESTE DA FUNÇÃO (pytest e/ou E2E do fluxo)
        ↓
falhou? → AJUSTAR E CORRIGIR → retestar
        ↓
CHECAGEM DE NEGÓCIO + SEGURANÇA
        ↓
commit sem segredos
        ↓
só então a próxima feature
```

Não pular etapa. Não misturar várias features grandes no mesmo PR/commit
sem necessidade.

---

## 3. Antes de codar — checklist de negócio

Responda por escrito no plano:

| Pergunta | Exemplo |
|----------|---------|
| Quem usa? | Consultora / funcionário / órgão / TI |
| Qual problema resolve? | Uma frase |
| O que o usuário vê/faz? | Fluxo em 3–5 passos |
| O que **não** muda? | Ex.: painel continua agregado |
| Conflita com anonimato, papéis ou multi-tenant? | Sim/não + como evita |
| Precisa migration? | Sim → Alembic reversível; nunca `create_all` em produção |

Se não encaixa na regra de negócio atual do Orizon, **não implementar**
(ou marcar como fora de escopo / P3 produto).

---

## 4. Durante a implementação — leve e sem conflito

- Uma fase / um módulo por vez.
- Preferir estender service/router existentes a criar caminhos paralelos
  de autorização (usar `app/core/autorizacao.py`).
- Soft delete (`deleted_at`) e `atualizado_em` nas mutations.
- Sem senha, token cru, JWT_SECRET ou chave R2/SendGrid em resposta,
  log ou commit.
- Frontend: UX apenas; **backend** é a autoridade de segurança.
- Não alterar comportamento de CLIMA/anonimato, bootstrap em produção
  ou IDOR→404 sem plano explícito e testes.

---

## 5. Depois do código — teste e correção

Obrigatório antes de considerar a feature “pronta”:

1. **Função** — o happy path faz o que o plano prometeu.
2. **Falha controlada** — entrada inválida, sem auth, papel errado,
   outro projeto → status esperado (em geral 404/422/401).
3. **Regressão** — suite relevante (`pytest`) continua verde.
4. Se falhar: **corrigir e retestar**; não “deixar para depois” em P0/P1.

Profundidade proporcional ao risco (auth, pesquisa, dados de pessoas =
mais testes).

---

## 6. Critério de aceite (Definition of Done)

A feature só está aceita quando:

- [ ] Propósito e regra de negócio documentados no plano/commit
- [ ] Implementação enxuta, sem conflito com fluxos críticos
- [ ] Segurança de escopo verificada (pelo menos casos cruzados relevantes)
- [ ] Testes da função passando; falhas encontradas foram corrigidas
- [ ] Sem segredos no diff; `.env` não commitado
- [ ] Migration (se houver) reversível e explicada

---

## 7. O que este documento proíbe

- Feature “só na tela” sem regra no backend
- Atalho que reabre buracos da auditoria (bootstrap público em prod,
  revelar respondente em clima, confiar só no React)
- Empilhar OKR / IA / feed / infra pesada antes do núcleo estar
  comprovado (`docs/AUDITORIA_2026-09.md`)

---

## 8. Ordem atual de trabalho (lembrete)

P0 (segurança crítica) → P1 (endurecimento) → P2 (operação/carga) →
P3 (produto novo).

Toda feature nova deve respeitar essa fila, salvo decisão explícita
do responsável do projeto.
