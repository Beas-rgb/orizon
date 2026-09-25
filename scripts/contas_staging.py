"""Semeia 32 funcionários de teste no staging. Nunca em produção.

Uso (só com HORIZON_AMBIENTE=staging):
  HORIZON_AMBIENTE=staging \\
  HORIZON_STAGING_URL=https://... \\
  HORIZON_STAGING_TOKEN=... \\
  HORIZON_STAGING_PROJETO_ID=... \\
    python scripts/contas_staging.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.carga_lib import recusar_producao

TOTAL_FUNCIONARIOS = 32


def csv_dataset(n: int = TOTAL_FUNCIONARIOS) -> bytes:
    linhas = ["nome;email;cargo;setor;superior_email"]
    linhas.append(
        "Presidente Teste;presidente.teste@staging.orizon.local;"
        "Presidente;Gabinete;"
    )
    for i in range(1, n):
        email = f"func{i:02d}.teste@staging.orizon.local"
        cargo = "Diretor" if i <= 5 else "Analista"
        setor = f"Setor {(i % 6) + 1}"
        superior = (
            "presidente.teste@staging.orizon.local"
            if i <= 5
            else "func01.teste@staging.orizon.local"
        )
        linhas.append(f"Funcionario {i:02d};{email};{cargo};{setor};{superior}")
    return "\n".join(linhas).encode("utf-8")


def _env() -> tuple[str, str, str]:
    if os.environ.get("HORIZON_AMBIENTE") != "staging":
        raise SystemExit("Recusado: defina HORIZON_AMBIENTE=staging.")
    url = os.environ.get("HORIZON_STAGING_URL", "").rstrip("/")
    token = os.environ.get("HORIZON_STAGING_TOKEN", "")
    projeto = os.environ.get("HORIZON_STAGING_PROJETO_ID", "")
    if not url or not token or not projeto:
        raise SystemExit("Faltam HORIZON_STAGING_URL, TOKEN ou PROJETO_ID.")
    recusar_producao(url)
    return url, token, projeto


def _post(url: str, token: str, caminho: str, body: bytes, content_type: str) -> dict:
    req = urllib.request.Request(
        f"{url}{caminho}",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode()[:200]
        raise SystemExit(f"HTTP {exc.code}: {detalhe}") from exc


def main() -> None:
    url, token, projeto = _env()
    csv = csv_dataset()
    boundary = "orizonbootdataset"
    corpo = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="arquivo"; '
        'filename="dataset.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode() + csv + f"\r\n--{boundary}--\r\n".encode()
    previa = _post(
        url,
        token,
        f"/projetos/{projeto}/importar/previa",
        corpo,
        f"multipart/form-data; boundary={boundary}",
    )
    print("previa_validos", previa.get("validos"), "invalidos", previa.get("invalidos"))
    confirmar = _post(
        url,
        token,
        f"/projetos/{projeto}/importar/confirmar",
        json.dumps({"linhas": previa.get("linhas", [])}).encode(),
        "application/json",
    )
    print("criados", confirmar.get("criados"), "total", confirmar.get("total"))


if __name__ == "__main__":
    main()
