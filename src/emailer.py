import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_report(to: str, subject: str, html: str, text: str) -> None:
    """Envia o relatório por email via SMTP com TLS.

    Args:
        to: Endereço de destino.
        subject: Assunto do email.
        html: Corpo em HTML.
        text: Corpo em texto simples (fallback).

    Raises:
        ValueError: Se as credenciais SMTP não estiverem configuradas no .env.
        smtplib.SMTPException: Em caso de falha no envio.
    """
    _validate_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_USER
    msg["To"] = to

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(config.EMAIL_USER, config.EMAIL_PASSWORD)
        smtp.sendmail(config.EMAIL_USER, to, msg.as_string())


def make_subject(origin: str, destination: str, lowest_price: float) -> str:
    """Gera o assunto do email com a rota e o menor preço encontrado."""
    return f"✈️ {origin} → {destination} | menor preço: R$ {lowest_price:,.0f}".replace(",", ".")


def _validate_config() -> None:
    missing = [
        name
        for name, val in [
            ("EMAIL_HOST", config.EMAIL_HOST),
            ("EMAIL_USER", config.EMAIL_USER),
            ("EMAIL_PASSWORD", config.EMAIL_PASSWORD),
        ]
        if not val
    ]
    if missing:
        raise ValueError(
            f"Credenciais SMTP não configuradas no .env: {', '.join(missing)}"
        )
