"""Fluxo de carga completo. Recusa produção. Não dispara a matriz sozinho.

Uso, só com staging:
  HORIZON_AMBIENTE=staging HORIZON_CARGA_URL=https://staging... \\
  HORIZON_CARGA_EMAIL=... HORIZON_CARGA_SENHA=... \\
    locust -f scripts/locustfile.py --headless -u 10 -r 2 -t 30s

Não rode contra o Render de produção. 1.000 usuários só depois do staging.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from scripts.carga_lib import recusar_producao


def preparar_alvo(url: str) -> str:
    limpa = url.strip()
    if not limpa:
        raise SystemExit("Defina HORIZON_CARGA_URL.")
    recusar_producao(limpa)
    host = urlparse(limpa).netloc.lower().split(":")[0]
    local = host in {"localhost", "127.0.0.1", "0.0.0.0"}
    if not local and os.environ.get("HORIZON_AMBIENTE") != "staging":
        raise SystemExit("Fora do localhost, defina HORIZON_AMBIENTE=staging.")
    return limpa.rstrip("/")


def _montar_usuario():
    from locust import HttpUser, between, task

    class FluxoResposta(HttpUser):
        """Login, perguntas, resposta e resultado. Mídia só se a pergunta tiver."""

        wait_time = between(1, 2)

        def on_start(self) -> None:
            email = os.environ.get("HORIZON_CARGA_EMAIL", "")
            senha = os.environ.get("HORIZON_CARGA_SENHA", "")
            if not email or not senha:
                raise SystemExit("Defina HORIZON_CARGA_EMAIL e HORIZON_CARGA_SENHA.")
            resp = self.client.post(
                "/auth/login",
                json={"email": email, "senha": senha},
                name="login",
            )
            if resp.status_code != 200:
                return
            token = resp.json().get("access_token", "")
            self.client.headers["Authorization"] = f"Bearer {token}"
            minhas = self.client.get("/eu/pesquisas", name="minhas")
            self.pesquisa_id = ""
            if minhas.status_code == 200 and minhas.json():
                self.pesquisa_id = minhas.json()[0].get("id", "")

        @task
        def responder(self) -> None:
            if not getattr(self, "pesquisa_id", ""):
                return
            pid = self.pesquisa_id
            form = self.client.get(
                f"/eu/pesquisas/{pid}/formulario",
                name="formulario",
            )
            if form.status_code != 200 or not form.json():
                return
            primeira = form.json()[0]
            if primeira.get("tem_midia"):
                self.client.get(
                    f"/eu/pesquisas/{pid}/perguntas/{primeira['id']}/midia",
                    name="midia",
                )
            corpo = {"respostas": []}
            for pergunta in form.json():
                if pergunta.get("tipo") in {"NOTA_5", "NOTA_10"}:
                    corpo["respostas"].append(
                        {"pergunta_id": pergunta["id"], "valor_numerico": 3}
                    )
            self.client.post(
                f"/eu/pesquisas/{pid}/responder",
                json=corpo,
                name="responder",
            )
            self.client.get(f"/eu/pesquisas/{pid}/nota", name="resultado")

    return FluxoResposta


_url = os.environ.get("HORIZON_CARGA_URL", "")
if _url:
    preparar_alvo(_url)
    try:
        FluxoResposta = _montar_usuario()
    except ImportError:
        FluxoResposta = None
