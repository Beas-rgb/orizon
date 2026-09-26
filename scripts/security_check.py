"""Bandit e pip-audit. Não fala com a API e não roda ZAP.

Uso, na raiz do repositório:
  python scripts/security_check.py
"""

from __future__ import annotations

import subprocess
import sys


def _rodar(modulo: str, args: list[str]) -> int:
    print("rodando", modulo)
    proc = subprocess.run(
        [sys.executable, "-m", modulo, *args],
        check=False,
    )
    return proc.returncode


def main() -> int:
    bandit = _rodar("bandit", ["-r", "app", "-ll", "-q"])
    audit = _rodar("pip_audit", [])
    if bandit == 0 and audit == 0:
        print("sem finding de severidade alta nestas ferramentas")
        return 0
    print("revise a saída. Finding aceito precisa de motivo no plano mestre.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
