import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


class MailerConfigError(RuntimeError):
    pass


def _validate_config() -> None:
    if not GMAIL_USER:
        raise MailerConfigError("Falta la variable de entorno GMAIL_USER")
    if not GMAIL_APP_PASSWORD:
        raise MailerConfigError("Falta la variable de entorno GMAIL_APP_PASSWORD")


def send_email(*, to_address: str, subject: str, body: str, attachment_path: Optional[str] = None) -> None:
    """Envía un correo con el PDF adjunto usando SMTP de Gmail."""
    _validate_config()

    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path:
        path = Path(attachment_path)
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo adjunto: {path}")
        with path.open("rb") as fh:
            data = fh.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)
