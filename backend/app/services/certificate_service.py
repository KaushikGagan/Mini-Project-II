"""Final PDF preparation and recoverable certificate issuance."""
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image as PilImage
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from ..extensions import db
from ..models import Certificate
from .fabric_gateway_service import FabricGatewayError, FabricUnavailable, get_certificate, register_certificate
from .hashing_service import calculate_file_sha256
from .qr_service import create_certificate_qr, verification_url

class CertificateIssuanceError(RuntimeError): pass

_NAVY   = colors.HexColor("#0D2137")
_LGOLD  = colors.HexColor("#D4AF37")
_CREAM  = colors.HexColor("#FFFDF5")
_DKGRAY = colors.HexColor("#374151")
_LTGRAY = colors.HexColor("#9CA3AF")
_WHITE  = colors.white


def _document_id(certificate_type):
    abbr = ''.join(c for c in ''.join(w[0] for w in certificate_type.split()).upper() if c.isalpha())
    return f"GOV-{abbr}-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"


def _goi_emblem_path(app_root: Path) -> Path:
    src = app_root / "static" / "images" / "goi_emblem.png"
    dest = app_root / "static" / "images" / "goi_emblem_transparent.png"
    if not dest.exists():
        img = PilImage.open(src).convert("RGBA")
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            # Make near-white pixels transparent
            if r > 220 and g > 220 and b > 220:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        img.save(str(dest), "PNG")
    return dest


def _wrap_text(pdf, text, x, y, max_width, font, size, line_height):
    pdf.setFont(font, size)
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if stringWidth(trial, font, size) > max_width:
            pdf.drawString(x, y, line)
            y -= line_height
            line = word
        else:
            line = trial
    if line:
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def _render_final_pdf(application, administrator, document_id, output_path, qr_path):
    issued_at = datetime.now(timezone.utc)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    pdf.setTitle(f"{application.certificate_type} - {document_id}")

    # Background
    pdf.setFillColor(_CREAM)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    # Outer border - navy thick
    pdf.setStrokeColor(_NAVY)
    pdf.setLineWidth(3)
    pdf.rect(10 * mm, 10 * mm, width - 20 * mm, height - 20 * mm, stroke=1, fill=0)

    # Inner border - gold thin
    pdf.setStrokeColor(_LGOLD)
    pdf.setLineWidth(1)
    pdf.rect(13 * mm, 13 * mm, width - 26 * mm, height - 26 * mm, stroke=1, fill=0)

    # Header band — taller to fit logo + text comfortably
    pdf.setFillColor(_NAVY)
    pdf.rect(10 * mm, height - 46 * mm, width - 20 * mm, 33 * mm, stroke=0, fill=1)

    # GoI emblem — left side, vertically centered in header
    emblem_path = _goi_emblem_path(Path(current_app.root_path))
    emblem_size = 26 * mm
    pdf.drawImage(str(emblem_path), 14 * mm, height - 44 * mm, width=emblem_size, height=emblem_size, preserveAspectRatio=True, anchor='c')

    # Header text — centered on full page width
    text_cx = width / 2
    pdf.setFillColor(_WHITE)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(text_cx, height - 22 * mm, "GOVERNMENT OF INDIA")
    pdf.setFillColor(_LGOLD)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(text_cx, height - 29 * mm, "MINISTRY OF CITIZEN SERVICES & DOCUMENT MANAGEMENT")
    pdf.setFillColor(_WHITE)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawCentredString(text_cx, height - 36 * mm, "Department of Citizen Services  |  e-Governance Division")

    # Gold divider
    pdf.setStrokeColor(_LGOLD)
    pdf.setLineWidth(1.5)
    pdf.line(18 * mm, height - 49 * mm, width - 18 * mm, height - 49 * mm)

    # Certificate title
    pdf.setFillColor(_NAVY)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 60 * mm, application.certificate_type.upper())
    title_w = stringWidth(application.certificate_type.upper(), "Helvetica-Bold", 18)
    pdf.setStrokeColor(_LGOLD)
    pdf.setLineWidth(0.8)
    pdf.line(width / 2 - title_w / 2, height - 62.5 * mm, width / 2 + title_w / 2, height - 62.5 * mm)

    # Cert number
    pdf.setFillColor(_DKGRAY)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width / 2, height - 67 * mm, f"Certificate No: CERT-{issued_at:%Y%m%d}-{application.application_id:06d}")

    # Details table
    lx, vx, row_h = 22 * mm, 75 * mm, 9 * mm
    y = height - 80 * mm
    rows = [
        ("Document ID",      document_id),
        ("Citizen Name",     application.citizen.full_name),
        ("Certificate Type", application.certificate_type),
        ("Application Ref",  application.reference_number),
        ("Date of Issue",    issued_at.strftime("%d %B %Y")),
    ]
    for label, value in rows:
        pdf.setFillColor(_NAVY)
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(lx, y, label + ":")
        pdf.setFillColor(_DKGRAY)
        pdf.setFont("Helvetica", 9.5)
        pdf.drawString(vx, y, value)
        y -= row_h

    # Divider
    y -= 3 * mm
    pdf.setStrokeColor(_LGOLD)
    pdf.setLineWidth(0.6)
    pdf.line(18 * mm, y, width - 18 * mm, y)
    y -= 7 * mm

    # Body text
    body = (
        f"This is to certify that {application.citizen.full_name} has submitted an application "
        f"for the issuance of a {application.certificate_type}. The application has been duly "
        f"reviewed and verified by the competent authority of the Department of Citizen Services, "
        f"Government of India. This certificate is issued for official and legal purposes and is "
        f"valid subject to the terms and conditions of the issuing authority."
    )
    pdf.setFillColor(_DKGRAY)
    y = _wrap_text(pdf, body, 22 * mm, y, width - 44 * mm, "Helvetica", 9.5, 6 * mm)

    # Blockchain notice
    y -= 4 * mm
    pdf.setFillColor(_NAVY)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(22 * mm, y, "Blockchain Registration:")
    pdf.setFillColor(_DKGRAY)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(75 * mm, y, "This certificate is immutably registered on Hyperledger Fabric.")

    # Footer
    footer_y = 52 * mm

    # QR code with white background
    pdf.setFillColor(_WHITE)
    pdf.rect(20 * mm, footer_y - 4 * mm, 34 * mm, 34 * mm, stroke=0, fill=1)
    pdf.drawImage(str(qr_path), 22 * mm, footer_y - 2 * mm, width=30 * mm, height=30 * mm, mask="auto")
    pdf.setFillColor(_DKGRAY)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawCentredString(37 * mm, footer_y - 8 * mm, "Scan to verify online")

    # Signature
    sig_path = Path(current_app.root_path) / "static" / "images" / "signature.jpeg"
    sig_w, sig_h = 52 * mm, 18 * mm
    sig_x = width - 22 * mm - sig_w
    sig_y = footer_y + 6 * mm
    if sig_path.exists():
        pdf.drawImage(str(sig_path), sig_x, sig_y, width=sig_w, height=sig_h, mask="auto")
    pdf.setStrokeColor(_NAVY)
    pdf.setLineWidth(0.6)
    pdf.line(sig_x, sig_y - 1 * mm, sig_x + sig_w, sig_y - 1 * mm)
    pdf.setFillColor(_NAVY)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawCentredString(sig_x + sig_w / 2, sig_y - 5 * mm, administrator.name)
    pdf.setFillColor(_DKGRAY)
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(sig_x + sig_w / 2, sig_y - 9 * mm, "Authorised Signatory")
    pdf.drawCentredString(sig_x + sig_w / 2, sig_y - 13 * mm, "Department of Citizen Services, GoI")

    # Bottom navy band
    pdf.setFillColor(_NAVY)
    pdf.rect(10 * mm, 10 * mm, width - 20 * mm, 16 * mm, stroke=0, fill=1)
    pdf.setFillColor(_LGOLD)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawCentredString(width / 2, 20 * mm, "GOVERNMENT OF INDIA  -  DEPARTMENT OF CITIZEN SERVICES  -  e-GOVERNANCE DIVISION")
    pdf.setFillColor(_WHITE)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawCentredString(width / 2, 15 * mm, f"Document ID: {document_id}")

    pdf.save()
    return issued_at


def _image_to_pdf(image_path: Path, output_path: Path):
    img = PilImage.open(image_path).convert("RGB")
    img.save(str(output_path), "PDF", resolution=150)


def _merge_uploaded_and_verification(upload_path: Path, verification_pdf: Path, output_path: Path):
    writer = PdfWriter()
    if upload_path.suffix.lower() == ".pdf":
        for page in PdfReader(str(upload_path)).pages:
            writer.add_page(page)
    else:
        tmp = output_path.with_suffix(".tmp.pdf")
        _image_to_pdf(upload_path, tmp)
        for page in PdfReader(str(tmp)).pages:
            writer.add_page(page)
        tmp.unlink(missing_ok=True)
    for page in PdfReader(str(verification_pdf)).pages:
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


def prepare_final_certificate(application, administrator):
    if application.certificate:
        return application.certificate
    document_id = _document_id(application.certificate_type)
    folder = Path(current_app.config["GENERATED_CERTIFICATES_FOLDER"])
    verification_pdf = folder / f"verification_{document_id}.pdf"
    output = folder / f"certificate_{document_id}.pdf"
    qr_path, _ = create_certificate_qr(document_id)
    issued_at = _render_final_pdf(application, administrator, document_id, verification_pdf, qr_path)
    upload_doc = application.documents.first()
    if upload_doc:
        upload_path = Path(current_app.config["UPLOAD_FOLDER"]) / upload_doc.stored_path
        _merge_uploaded_and_verification(upload_path, verification_pdf, output)
        verification_pdf.unlink(missing_ok=True)
    else:
        verification_pdf.rename(output)
    certificate = Certificate(
        application=application, document_id=document_id, pdf_path=output.name,
        qr_path=qr_path.name, issued_by=administrator, issued_date=issued_at,
        issuance_state="Blockchain Registration Pending"
    )
    certificate.sha256_hash = calculate_file_sha256(output)
    db.session.add(certificate)
    return certificate


def issue_certificate(application, administrator):
    certificate = prepare_final_certificate(application, administrator)
    if certificate.issuance_state == "Issued":
        return certificate
    application.status = "Issuance Pending"
    certificate.issuance_state = "Blockchain Registration Pending"
    certificate.issuance_attempts = (certificate.issuance_attempts or 0) + 1
    certificate.blockchain_error = None
    db.session.commit()
    try:
        result = register_certificate(certificate, administrator)
        record = result["record"]
        if record["sha256Hash"] != certificate.sha256_hash:
            raise CertificateIssuanceError("Document ID already exists with a different hash on Fabric.")
        certificate.blockchain_transaction_id = record.get("transactionId") or result.get("transactionId")
        certificate.blockchain_registered_at = datetime.now(timezone.utc)
        certificate.issuance_state = "Issued"
        certificate.blockchain_error = None
        application.status = "Issued"
        db.session.commit()
        return certificate
    except (FabricUnavailable, FabricGatewayError, CertificateIssuanceError) as error:
        db.session.rollback()
        certificate = Certificate.query.filter_by(application_id=application.application_id).first()
        certificate.issuance_state = "Issuance Failed"
        certificate.blockchain_error = str(error)[:2000]
        certificate.application.status = "Issuance Failed"
        db.session.commit()
        raise CertificateIssuanceError(str(error)) from error


def reconcile_certificate(certificate):
    record = get_certificate(certificate.document_id)["record"]
    if record["sha256Hash"] != certificate.sha256_hash:
        raise CertificateIssuanceError("Existing Fabric record hash differs from the finalized PDF.")
    certificate.blockchain_transaction_id = record.get("transactionId")
    certificate.blockchain_registered_at = datetime.now(timezone.utc)
    certificate.issuance_state = "Issued"
    certificate.blockchain_error = None
    certificate.application.status = "Issued"
    db.session.commit()
    return certificate


def certificate_verification_url(certificate):
    return verification_url(certificate.document_id)
