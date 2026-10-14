from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from ..extensions import db
from ..models import Certificate


def _document_id(certificate_type):
    prefix = "".join(word[0] for word in certificate_type.split()).upper()
    return f"GOV-{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"


def generate_certificate(application, administrator):
    """Create a non-blockchain certificate PDF. Hash/QR work is deliberately deferred."""
    if application.certificate:
        return application.certificate

    document_id = _document_id(application.certificate_type)
    filename = f"certificate_{document_id}.pdf"
    output_path = Path(current_app.config["GENERATED_CERTIFICATES_FOLDER"]) / filename
    certificate_number = f"CERT-{datetime.now(timezone.utc):%Y%m%d}-{application.application_id:06d}"
    issued_at = datetime.now(timezone.utc)

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    pdf.setTitle(f"{application.certificate_type} — {document_id}")
    pdf.setStrokeColor(colors.HexColor("#2563EB"))
    pdf.setLineWidth(2)
    pdf.rect(14 * mm, 14 * mm, width - 28 * mm, height - 28 * mm)
    pdf.setFillColor(colors.HexColor("#0B1120"))
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 29 * mm, "GOVERNMENT DOCUMENT MANAGEMENT SYSTEM")
    pdf.setFillColor(colors.HexColor("#2563EB"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawCentredString(width / 2, height - 36 * mm, "DEPARTMENT OF CITIZEN SERVICES")
    pdf.setStrokeColor(colors.HexColor("#64748B"))
    pdf.rect(18 * mm, height - 55 * mm, 24 * mm, 16 * mm)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(30 * mm, height - 47 * mm, "GOVERNMENT")
    pdf.drawCentredString(30 * mm, height - 51 * mm, "LOGO")
    pdf.setFillColor(colors.HexColor("#0B1120"))
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, height - 66 * mm, application.certificate_type.upper())
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width / 2, height - 73 * mm, f"Certificate No: {certificate_number}")

    x, y = 28 * mm, height - 94 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, "Document ID:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x + 35 * mm, y, document_id)
    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, "Citizen Name:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x + 35 * mm, y, application.citizen.full_name)
    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, "Application ID:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x + 35 * mm, y, application.reference_number)
    y -= 20 * mm
    content = (
        f"This is to certify that the application submitted by {application.citizen.full_name} "
        f"has been reviewed and approved by the Department of Citizen Services. "
        f"This {application.certificate_type.lower()} is issued for official purposes."
    )
    pdf.setFont("Helvetica", 11)
    words, line = content.split(), ""
    for word in words:
        trial = f"{line} {word}".strip()
        if stringWidth(trial, "Helvetica", 11) > width - 56 * mm:
            pdf.drawString(x, y, line)
            y -= 7 * mm
            line = word
        else:
            line = trial
    pdf.drawString(x, y, line)
    y -= 35 * mm
    pdf.setFont("Helvetica", 9)
    pdf.drawString(x, y, f"Issue Date: {issued_at:%d %B %Y}")
    pdf.drawRightString(width - 28 * mm, y, f"Authorized by: {administrator.name}")
    y -= 18 * mm
    pdf.setStrokeColor(colors.HexColor("#475569"))
    pdf.line(width - 82 * mm, y, width - 28 * mm, y)
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - 28 * mm, y - 5 * mm, "Official Signature Placeholder")
    pdf.circle(33 * mm, y - 3 * mm, 13 * mm)
    pdf.drawCentredString(33 * mm, y - 4 * mm, "OFFICIAL SEAL")
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawCentredString(width / 2, 21 * mm, "Government Document Management and Verification System")
    pdf.save()

    certificate = Certificate(
        application=application,
        document_id=document_id,
        pdf_path=filename,
        issued_date=issued_at,
        issued_by=administrator,
    )
    db.session.add(certificate)
    return certificate
