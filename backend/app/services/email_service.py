
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
import re
import smtplib
import ssl

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.db.session import SessionLocal
from app.models.email_log import EmailDeliveryLog


TEMPLATE_DIR = BACKEND_DIR / "app" / "templates" / "emails"

ALLOWED_TEMPLATES = {
    "employee_onboarding.html",
    "leave_applied.html",
    "leave_status.html",
    "leave_for_review.html",
    "payroll_processed.html",
    "salary_slip_generated.html",
}

email_environment = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def deliver_email_log(email_log_id: int) -> None:
    """Deliver a queued email in a separate database session."""

    with SessionLocal() as db:
        log = db.get(EmailDeliveryLog, email_log_id)

        if log is None or log.status != "PENDING":
            return

        log.attempt_count += 1
        log.last_attempt_at = datetime.now(timezone.utc)

        smtp_is_configured = (
            settings.smtp_enabled
            and bool(settings.smtp_host)
            and bool(settings.smtp_from_email)
        )

        if not smtp_is_configured:
            log.status = "SKIPPED"
            log.error_message = (
                "SMTP is disabled or required SMTP settings are missing."
            )
            db.commit()
            return

        if log.template_name not in ALLOWED_TEMPLATES:
            log.status = "FAILED"
            log.error_message = "Email template is not permitted."
            db.commit()
            return

        try:
            template = email_environment.get_template(log.template_name)
            html_body = template.render(**log.email_context)

            plain_body = re.sub(r"<[^>]+>", " ", html_body)
            plain_body = " ".join(plain_body.split())

            message = EmailMessage()
            message["Subject"] = log.subject
            message["From"] = settings.smtp_from_email
            message["To"] = log.recipient_email
            message.set_content(plain_body)
            message.add_alternative(html_body, subtype="html")

            context = ssl.create_default_context()

            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as server:
                if settings.smtp_use_tls:
                    server.starttls(context=context)

                if settings.smtp_username and settings.smtp_password:
                    server.login(
                        settings.smtp_username,
                        settings.smtp_password.get_secret_value(),
                    )

                server.send_message(message)

            log.status = "SENT"
            log.sent_at = datetime.now(timezone.utc)
            log.error_message = None

        except Exception as exc:
            log.status = "FAILED"
            log.error_message = (
                f"{type(exc).__name__}: {str(exc)[:500]}"
            )

        db.commit()
