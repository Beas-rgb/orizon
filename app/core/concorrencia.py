"""Fila do Argon2. O Free não aguenta dezenas de hashes ao mesmo tempo."""

import threading
import time

from app.core.config import settings

MSG_OCUPADO = "Sistema ocupado. Tente novamente em instantes."


class SistemaOcupado(Exception):
    """A fila do hash lotou ou estourou o tempo de espera."""


class LimiteHash:
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._em_curso = 0
        self._fila = 0

    @property
    def em_curso(self) -> int:
        with self._cond:
            return self._em_curso

    def executar(self, funcao):
        max_curso = settings.auth_hash_max_concurrency
        max_fila = settings.auth_hash_max_fila
        prazo = time.monotonic() + settings.auth_hash_timeout_s
        with self._cond:
            if self._em_curso >= max_curso and self._fila >= max_fila:
                raise SistemaOcupado()
            self._fila += 1
            try:
                while self._em_curso >= max_curso:
                    restante = prazo - time.monotonic()
                    if restante <= 0:
                        raise SistemaOcupado()
                    self._cond.wait(restante)
                self._em_curso += 1
            finally:
                self._fila -= 1
        try:
            return funcao()
        finally:
            with self._cond:
                self._em_curso -= 1
                self._cond.notify()


limite_hash = LimiteHash()
