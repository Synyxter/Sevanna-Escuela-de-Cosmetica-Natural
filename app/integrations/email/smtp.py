"""SMTP email provider (async via aiosmtplib).

Works with any SMTP server (Gmail, Zoho, etc.) using credentials from settings.
"""

from __future__ import annotations

from email.message import EmailMessage as MIMEMessage

import aiosmtplib

from app.core.config import settings
from app.integrations.email.base import EmailMessage, EmailProvider


class SMTPEmailProvider(EmailProvider):
    name = "smtp"

    async def send(self, message: EmailMessage) -> None:
        mime = MIMEMessage()
        mime["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text_body or "Consulta este correo en un cliente compatible.")
        mime.add_alternative(message.html_body, subtype="html")

        await aiosmtplib.send(
            mime,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
            timeout=20,
        )
