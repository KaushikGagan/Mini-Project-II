"""Transactional email notifications for certificate lifecycle events."""
import smtplib

from flask import current_app
from flask_mail import Message

from ..extensions import mail


def _send(subject: str, recipient: str, body: str) -> None:
    if not all([current_app.config.get("MAIL_USERNAME"), current_app.config.get("MAIL_PASSWORD"), current_app.config.get("MAIL_DEFAULT_SENDER")]):
        current_app.logger.warning("Email not configured — skipping notification to %s", recipient)
        return
    try:
        mail.send(Message(subject=subject, recipients=[recipient], body=body))
    except (smtplib.SMTPException, OSError, ConnectionError) as error:
        current_app.logger.error("Email delivery failed to %s: %s", recipient, type(error).__name__)


def send_issuance_email(certificate) -> None:
    citizen = certificate.application.citizen
    verify_url = f"{current_app.config['VERIFICATION_BASE_URL']}/verify?document_id={certificate.document_id}"
    _send(
        subject=f"Your {certificate.application.certificate_type} has been issued",
        recipient=citizen.email,
        body=(
            f"Dear {citizen.full_name},\n\n"
            f"Your {certificate.application.certificate_type} has been issued and registered on the blockchain.\n\n"
            f"Document ID: {certificate.document_id}\n"
            f"Application Reference: {certificate.application.reference_number}\n\n"
            f"You can download your certificate from your portal or verify it publicly at:\n{verify_url}\n\n"
            "Regards,\nGovernment Document Management System"
        ),
    )


def send_rejection_email(application) -> None:
    citizen = application.citizen
    _send(
        subject=f"Update on your {application.certificate_type} application",
        recipient=citizen.email,
        body=(
            f"Dear {citizen.full_name},\n\n"
            f"Your application ({application.reference_number}) for a {application.certificate_type} "
            f"has been updated to status: {application.status}.\n\n"
            f"Remarks from the reviewer:\n{application.remarks or 'No remarks provided.'}\n\n"
            "If you have questions, please contact the department.\n\n"
            "Regards,\nGovernment Document Management System"
        ),
    )


def send_revocation_email(certificate) -> None:
    citizen = certificate.application.citizen
    _send(
        subject=f"Your {certificate.application.certificate_type} has been revoked",
        recipient=citizen.email,
        body=(
            f"Dear {citizen.full_name},\n\n"
            f"Your {certificate.application.certificate_type} (Document ID: {certificate.document_id}) "
            "has been revoked by the issuing authority and is no longer valid.\n\n"
            "Please contact the department for further information.\n\n"
            "Regards,\nGovernment Document Management System"
        ),
    )
