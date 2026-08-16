"""Plain email templates. Returns (subject, html_body, text_body) tuples.

Kept intentionally simple and self-contained (no external template engine) for
the first version. Content is transactional and localized in Spanish.
"""

from __future__ import annotations

from app.core.config import settings


def _wrap(title: str, body_html: str) -> str:
    return (
        f"<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;"
        f"color:#2b2b2b'>"
        f"<h2 style='color:#6b8e5a'>{title}</h2>{body_html}"
        f"<hr style='border:none;border-top:1px solid #eee;margin:24px 0'>"
        f"<p style='font-size:12px;color:#999'>{settings.email_from_name} — "
        f"Academia de cosmética natural</p></div>"
    )


def verification_email(full_name: str, verify_link: str) -> tuple[str, str, str]:
    subject = "Verifica tu correo en Sevanna"
    html = _wrap(
        "Confirma tu cuenta",
        f"<p>Hola {full_name},</p>"
        f"<p>Gracias por registrarte en Sevanna. Confirma tu correo:</p>"
        f"<p><a href='{verify_link}' style='background:#6b8e5a;color:#fff;"
        f"padding:10px 18px;border-radius:6px;text-decoration:none'>"
        f"Verificar correo</a></p>"
        f"<p>O copia este enlace: {verify_link}</p>",
    )
    text = f"Hola {full_name}, verifica tu correo: {verify_link}"
    return subject, html, text


def password_reset_email(full_name: str, reset_link: str) -> tuple[str, str, str]:
    subject = "Restablece tu contraseña en Sevanna"
    html = _wrap(
        "Restablecer contraseña",
        f"<p>Hola {full_name},</p>"
        f"<p>Recibimos una solicitud para restablecer tu contraseña. "
        f"Si no fuiste tú, ignora este correo.</p>"
        f"<p><a href='{reset_link}' style='background:#6b8e5a;color:#fff;"
        f"padding:10px 18px;border-radius:6px;text-decoration:none'>"
        f"Cambiar contraseña</a></p>"
        f"<p>Este enlace caduca pronto.</p>",
    )
    text = f"Hola {full_name}, restablece tu contraseña: {reset_link}"
    return subject, html, text


def purchase_confirmation_email(
    full_name: str,
    course_title: str,
    modality: str,
    whatsapp_url: str | None,
    google_meet_url: str | None,
) -> tuple[str, str, str]:
    subject = f"Confirmación de compra — {course_title}"
    links = ""
    if whatsapp_url:
        links += f"<li>WhatsApp del grupo: <a href='{whatsapp_url}'>{whatsapp_url}</a></li>"
    if google_meet_url:
        links += f"<li>Google Meet: <a href='{google_meet_url}'>{google_meet_url}</a></li>"
    links_block = f"<ul>{links}</ul>" if links else "<p>Pronto recibirás los enlaces de acceso.</p>"

    html = _wrap(
        "¡Compra confirmada!",
        f"<p>Hola {full_name},</p>"
        f"<p>Tu compra del curso <strong>{course_title}</strong> "
        f"(modalidad {modality}) fue confirmada.</p>"
        f"<p>Estos son tus accesos:</p>{links_block}"
        f"<p>Puedes ver tus cursos en cualquier momento desde tu cuenta.</p>",
    )
    text = (
        f"Hola {full_name}, tu compra de '{course_title}' ({modality}) fue confirmada. "
        f"WhatsApp: {whatsapp_url or '-'} | Meet: {google_meet_url or '-'}"
    )
    return subject, html, text
