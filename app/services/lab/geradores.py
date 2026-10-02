"""Geradores determinísticos. Nunca usam o random global."""

from __future__ import annotations

import random

from app.services.importacao import LinhaImportacao

TAMANHOS = frozenset({100, 250, 500, 1000, 5000})
PERFIS = frozenset({"ALEATORIO", "POSITIVO", "NEUTRO", "NEGATIVO"})
TIPOS_CENARIO = frozenset({"CLIMA", "DESEMPENHO"})
DOMINIO = "sintetico.invalid"
LEQUE = 6
PROFUNDIDADE_MAX = 5


def rng_de(seed: int, chave: str) -> random.Random:
    return random.Random(f"{seed}:{chave}")


def digito_cnpj(numeros: list[int], pesos: list[int]) -> int:
    soma = sum(n * p for n, p in zip(numeros, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_sintetico(seed: int, sufixo: str) -> str:
    """CNPJ com dígitos verificadores válidos. Sem consulta externa."""
    rng = rng_de(seed, f"cnpj:{sufixo}")
    base = [rng.randint(0, 9) for _ in range(12)]
    if len(set(base)) == 1:
        base[-1] = (base[-1] + 1) % 10
    d1 = digito_cnpj(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito_cnpj(base + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return "".join(str(d) for d in base + [d1, d2])


def email_sintetico(indice: int, cenario_id: str) -> str:
    return f"s{indice}.{cenario_id[:8]}@{DOMINIO}"


def n_setores(tamanho: int) -> int:
    if tamanho <= 100:
        return 5
    if tamanho <= 250:
        return 8
    if tamanho <= 500:
        return 12
    if tamanho <= 1000:
        return 16
    return 20


def montar_linhas(
    tamanho: int,
    seed: int,
    cenario_id: str,
) -> list[LinhaImportacao]:
    """Hierarquia em leque de 6, profundidade ≤ 5. Um superior por nível."""
    _ = seed  # seed reserva estabilidade futura dos nomes/cargos
    setores = [f"Setor {i + 1}" for i in range(n_setores(tamanho))]
    cargos = [f"Cargo {i + 1}" for i in range(10)]
    emails = [email_sintetico(i, cenario_id) for i in range(tamanho)]
    superiores: list[str | None] = [None] * tamanho
    profundidade = [0] * tamanho
    proximo_pai = 0
    filhos_do_pai = 0
    for i in range(1, tamanho):
        while (
            profundidade[proximo_pai] >= PROFUNDIDADE_MAX
            or filhos_do_pai >= LEQUE
        ):
            proximo_pai += 1
            filhos_do_pai = 0
            if proximo_pai >= i:
                proximo_pai = max(0, i - 1)
                break
        superiores[i] = emails[proximo_pai]
        profundidade[i] = profundidade[proximo_pai] + 1
        filhos_do_pai += 1
        if filhos_do_pai >= LEQUE:
            proximo_pai += 1
            filhos_do_pai = 0

    linhas: list[LinhaImportacao] = []
    for i, email in enumerate(emails):
        linhas.append(
            LinhaImportacao(
                nome=f"Sintetico {i + 1}",
                email=email,
                cargo=cargos[i % len(cargos)],
                setor=setores[i % len(setores)],
                superior_email=superiores[i] or "",
                erros=[],
            )
        )
    # Ordem topologica: o pai (indice menor) entra antes do filho.
    return linhas


def perguntas_clima() -> list[dict[str, object]]:
    """12 perguntas cobrindo todos os TIPOS_PERGUNTA."""
    return [
        {"texto": "Como avalia o clima?", "tipo": "NOTA_5", "opcoes": []},
        {"texto": "Nota geral do ambiente", "tipo": "NOTA_10", "opcoes": []},
        {
            "texto": "Recomendaria o órgão?",
            "tipo": "SIM_NAO",
            "opcoes": ["Sim", "Não"],
        },
        {
            "texto": "Principal fator",
            "tipo": "MULTIPLA_ESCOLHA",
            "opcoes": ["Lideranca", "Equipe", "Recursos", "Processos"],
        },
        {
            "texto": "O que pode melhorar",
            "tipo": "CHECKBOX",
            "opcoes": ["Comunicacao", "Carga", "Reconhecimento", "Ferramentas"],
        },
        {
            "texto": "Comente livremente",
            "tipo": "TEXTO_LIVRE",
            "opcoes": [],
        },
        {"texto": "Satisfacao com a chefia", "tipo": "NOTA_5", "opcoes": []},
        {"texto": "Satisfacao com a equipe", "tipo": "NOTA_5", "opcoes": []},
        {
            "texto": "Ha assedio?",
            "tipo": "SIM_NAO",
            "opcoes": ["Sim", "Não"],
        },
        {
            "texto": "Canal preferido",
            "tipo": "MULTIPLA_ESCOLHA",
            "opcoes": ["Email", "Reuniao", "Chat"],
        },
        {
            "texto": "Recursos usados",
            "tipo": "CHECKBOX",
            "opcoes": ["Notebook", "Sistema", "Sala", "Transporte"],
        },
        {
            "texto": "Sugestao final",
            "tipo": "TEXTO_LIVRE",
            "opcoes": [],
        },
    ]
