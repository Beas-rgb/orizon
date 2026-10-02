"""Oráculo: recalcula o resultado sem usar o motor do painel."""

from __future__ import annotations

from collections import defaultdict

from app.services.pesquisa.comum import K_ANONIMATO
from app.services.pesquisa.desempenho import PESOS_PADRAO


def media_notas(valores: list[float]) -> float | None:
    if not valores:
        return None
    return sum(valores) / len(valores)


def deve_suprimir(respondentes: int, anonimo: bool = True) -> bool:
    return anonimo and respondentes < K_ANONIMATO


def media_ponderada_desempenho(
    por_perspectiva: dict[str, float],
    pesos: dict[str, float] | None = None,
) -> float | None:
    """Mesma fórmula do motor, escrita de novo para o teste comparar."""
    tabela = pesos or PESOS_PADRAO
    if not por_perspectiva:
        return None
    soma_pesos = sum(tabela.get(tipo, 0.0) for tipo in por_perspectiva)
    if soma_pesos == 0:
        return None
    return (
        sum(
            por_perspectiva[tipo] * tabela.get(tipo, 0.0)
            for tipo in por_perspectiva
        )
        / soma_pesos
    )


def distribuicao_opcoes(
    escolhas: list[str],
) -> dict[str, int]:
    contagem: dict[str, int] = defaultdict(int)
    for item in escolhas:
        contagem[item] += 1
    return dict(contagem)


def conferir_nota5(
    painel_item: dict,
    valores_esperados: list[float],
    *,
    anonimo: bool = True,
) -> None:
    respondentes = len(valores_esperados)
    if deve_suprimir(respondentes, anonimo):
        assert painel_item["suprimido"] is True
        assert painel_item["media"] is None
        return
    assert painel_item["suprimido"] is False
    media = media_notas(valores_esperados)
    assert media is not None
    assert abs(float(painel_item["media"]) - media) < 1e-6
