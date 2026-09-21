"""Envio de e-mail. SendGrid (API HTTPS) tem prioridade; Mailtrap e SMTP de reserva.

No plano free do Render as portas SMTP (587/465) ficam bloqueadas — por isso
a API HTTPS (SendGrid) é o caminho para demo real. Sem provedor, em development
grava numa caixa local. O token viaja no e-mail; a API nunca devolve senha.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

OUTBOX = Path("data/outbox")


class EmailNaoEnviado(Exception):
    pass


@dataclass(frozen=True)
class ResultadoEmail:
    """Aceite técnico do provedor; não significa entrega na caixa de entrada."""

    provedor: str
    mensagem_id: str | None = None


def modo_envio() -> str:
    """Só o nome do canal. Nunca devolve token, senha ou host."""
    if settings.sendgrid_api_key:
        return "sendgrid"
    if settings.mailtrap_api_token:
        return "mailtrap"
    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        return "smtp"
    return "local"


def _tem_provedor_remoto() -> bool:
    return bool(
        settings.sendgrid_api_key
        or settings.mailtrap_api_token
        or settings.smtp_host
    )


def _corpo_para_html(corpo: str) -> str:
    """HTML simples com links clicáveis (clientes que abrem só a parte HTML)."""
    escapado = html_lib.escape(corpo)
    com_links = re.sub(
        r"https?://[^\s<&]+",
        lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>',
        escapado,
    )
    return (
        '<div style="font-family:system-ui,sans-serif;font-size:14px;'
        'line-height:1.5;white-space:pre-wrap">'
        f"{com_links}"
        "</div>"
    )


class CaixaEmail:
    """Testes substituem esta caixa e leem o que sairia no e-mail."""

    def __init__(self) -> None:
        self.mensagens: list[dict[str, str]] = []

    def enviar(
        self,
        destino: str,
        assunto: str,
        corpo: str,
        categoria: str = "Horizon",
    ) -> ResultadoEmail:
        self.mensagens.append(
            {"destino": destino, "assunto": assunto, "corpo": corpo}
        )
        # Em development sempre grava a caixa local, mesmo com provedor remoto.
        # Assim o TI recupera o token se o e-mail real não chegar.
        if settings.app_env == "development" or not _tem_provedor_remoto():
            self._gravar_outbox(destino, assunto, corpo)
        erros: list[str] = []
        if settings.sendgrid_api_key:
            try:
                return _enviar_sendgrid(destino, assunto, corpo, categoria)
            except EmailNaoEnviado as exc:
                erros.append(f"SendGrid: {exc}")
        if settings.mailtrap_api_token:
            try:
                return _enviar_mailtrap(destino, assunto, corpo, categoria)
            except EmailNaoEnviado as exc:
                erros.append(f"Mailtrap: {exc}")
        if settings.smtp_host:
            try:
                return _enviar_smtp(destino, assunto, corpo)
            except Exception as exc:
                erros.append(f"SMTP: {exc}")
        if erros:
            raise EmailNaoEnviado(" | ".join(erros))
        return ResultadoEmail(provedor="local")

    def _gravar_outbox(self, destino: str, assunto: str, corpo: str) -> None:
        OUTBOX.mkdir(parents=True, exist_ok=True)
        arquivo = OUTBOX / "ultimo.txt"
        arquivo.write_text(
            f"para: {destino}\nassunto: {assunto}\n\n{corpo}\n",
            encoding="utf-8",
        )


caixa_email = CaixaEmail()


def _enviar_sendgrid(
    destino: str,
    assunto: str,
    corpo: str,
    categoria: str,
) -> ResultadoEmail:
    remetente = settings.sendgrid_from_email or settings.smtp_from
    if not remetente:
        raise EmailNaoEnviado(
            "Remetente SendGrid não configurado (SENDGRID_FROM_EMAIL)"
        )
    nome = settings.sendgrid_from_name or "Horizon"
    payload = {
        "personalizations": [
            {
                "to": [{"email": destino}],
                "custom_args": {"categoria": categoria[:64]},
            }
        ],
        "from": {"email": remetente, "name": nome},
        "subject": assunto,
        "content": [
            {"type": "text/plain", "value": corpo},
            {"type": "text/html", "value": _corpo_para_html(corpo)},
        ],
    }
    pedido = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=20) as resposta:
            # 202 Accepted = enviado para a fila do SendGrid.
            if resposta.status not in (200, 202):
                raise EmailNaoEnviado(f"SendGrid status {resposta.status}")
            headers = getattr(resposta, "headers", {})
            return ResultadoEmail(
                provedor="sendgrid",
                mensagem_id=headers.get("X-Message-Id"),
            )
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")[:200]
        raise EmailNaoEnviado(f"SendGrid HTTP {exc.code}: {detalhe}") from None
    except urllib.error.URLError as exc:
        raise EmailNaoEnviado(f"SendGrid rede: {exc.reason}") from None


def _enviar_mailtrap(
    destino: str, assunto: str, corpo: str, categoria: str
) -> ResultadoEmail:
    import socket

    import mailtrap as mt

    remetente = settings.mailtrap_from_email or settings.smtp_from
    if not remetente:
        raise EmailNaoEnviado("Remetente Mailtrap não configurado")
    mail = mt.Mail(
        sender=mt.Address(
            email=remetente,
            name=settings.mailtrap_from_name or "Horizon",
        ),
        to=[mt.Address(email=destino)],
        subject=assunto,
        text=corpo,
        category=categoria,
    )
    client = mt.MailtrapClient(token=settings.mailtrap_api_token)
    antigo = socket.getdefaulttimeout()
    socket.setdefaulttimeout(20)
    try:
        resposta = client.send(mail)
        mensagem_id = None
        if isinstance(resposta, dict):
            ids = resposta.get("message_ids")
            if isinstance(ids, list) and ids:
                mensagem_id = str(ids[0])
        return ResultadoEmail(provedor="mailtrap", mensagem_id=mensagem_id)
    except Exception as exc:
        raise EmailNaoEnviado(f"Mailtrap: {exc}") from exc
    finally:
        socket.setdefaulttimeout(antigo)


def _enviar_smtp(
    destino: str,
    assunto: str,
    corpo: str,
) -> ResultadoEmail:
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = destino
    msg.set_content(corpo)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return ResultadoEmail(provedor="smtp")
