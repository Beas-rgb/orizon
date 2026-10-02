"""A fila do hash não passa do limite e responde 503 quando lota."""

import threading
import time

from app.core.concorrencia import SistemaOcupado, limite_hash
from app.core.config import settings


def test_fila_cheio_responde_503_e_nao_passa_do_limite(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_hash_max_concurrency", 1)
    monkeypatch.setattr(settings, "auth_hash_max_fila", 2)
    monkeypatch.setattr(settings, "auth_hash_timeout_s", 2)
    pico = 0
    trava = threading.Lock()
    entrar = threading.Barrier(6)
    resultados: list[str] = []

    def lento() -> str:
        nonlocal pico
        with trava:
            pico = max(pico, limite_hash.em_curso)
        time.sleep(0.2)
        return "ok"

    def trabalhador() -> None:
        entrar.wait()
        try:
            limite_hash.executar(lento)
            resultados.append("ok")
        except SistemaOcupado:
            resultados.append("503")

    fios = [threading.Thread(target=trabalhador) for _ in range(6)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    assert resultados.count("503") >= 1
    assert resultados.count("ok") >= 1
    assert pico <= 1


def test_login_ocupado_envia_retry_after(client, monkeypatch) -> None:
    def estoura(_funcao):
        raise SistemaOcupado()

    monkeypatch.setattr("app.core.security.limite_hash.executar", estoura)
    resposta = client.post(
        "/auth/login",
        json={"email": "ninguem@horizon.dev", "senha": "Senha-segura1"},
    )
    assert resposta.status_code == 503
    assert resposta.headers["retry-after"] == "5"
    assert resposta.json()["detail"] == "Sistema ocupado. Tente novamente em instantes."
