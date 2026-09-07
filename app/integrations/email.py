"""Envio de e-mail. Sem SMTP, em desenvolvimento grava numa caixa local.

O token viaja no e-mail. A resposta da API nunca devolve senha nem token.
Isso evita que um cliente malicioso leia o segredo só por chamar a rota.
"""

from pathlib import Path

from app.core.config import settings

OUTBOX = Path("data/outbox")


class EmailNaoEnviado(Exception):
    pass


class CaixaEmail:
    """Testes substituem esta caixa e leem o que sairia no e-mail."""

    def __init__(self) -> None:
        self.mensagens: list[dict[str, str]] = []

    def enviar(self, destino: str, assunto: str, corpo: str) -> None:
        self.mensagens.append(
            {"destino": destino, "assunto": assunto, "corpo": corpo}
        )
        if settings.smtp_host:
            _enviar_smtp(destino, assunto, corpo)
            return
        if settings.app_env != "development":
            raise EmailNaoEnviado("SMTP não configurado")
        OUTBOX.mkdir(parents=True, exist_ok=True)
        arquivo = OUTBOX / "ultimo.txt"
        arquivo.write_text(
            f"para: {destino}\nassunto: {assunto}\n\n{corpo}\n",
            encoding="utf-8",
        )


caixa_email = CaixaEmail()


def _enviar_smtp(destino: str, assunto: str, corpo: str) -> None:
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
