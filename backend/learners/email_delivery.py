from django.conf import settings
from django.core.mail import EmailMessage, get_connection


def available():
    return (
        settings.SOMA_ENV in {"development", "test"}
        and settings.SOMA_ACCOUNT_EMAIL_MODE == "memory"
    )


def deliver_preview(recipient, purpose, raw_token):
    """Explicit in-memory backend only. Never print or send account secrets."""
    if not available():
        raise RuntimeError("Account email delivery is unavailable.")
    # Fixed local destination avoids request Host/header-derived token links.
    link = f"http://127.0.0.1:4177/account/{purpose}#token={raw_token}"
    expiry = "24 hours" if purpose == "verify" else "30 minutes"
    message = EmailMessage(
        subject="SOMA.i local account preview",
        body=f"Offline preview only; no email was sent.\nOpen {link}\nConfirm explicitly within {expiry}. Ignore this message if you did not request it.",
        from_email="preview@example.invalid",
        to=[recipient],
        connection=get_connection("django.core.mail.backends.locmem.EmailBackend"),
    )
    if message.send(fail_silently=False) != 1:
        raise RuntimeError("Account preview could not be stored.")
