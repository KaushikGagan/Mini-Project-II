"""Final PDF preparation and recoverable certificate issuance."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from flask import current_app
from pypdf import PdfWriter, PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from PIL import Image as PilImage
from ..extensions import db
from ..models import Certificate
from .fabric_gateway_service import FabricGatewayError, FabricUnavailable, get_certificate, register_certificate
from .hashing_service import calculate_file_sha256
from .qr_service import create_certificate_qr, verification_url

class CertificateIssuanceError(RuntimeError): pass

def _document_id(certificate_type):
    abbr = ''.join(c for c in ''.join(word[0] for word in certificate_type.split()).upper() if c.isalpha())
    return f"GOV-{abbr}-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"

def _render_final_pdf(application, administrator, document_id, output_path, qr_path):
    issued_at = datetime.now(timezone.utc)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    pdf.setTitle(f"{application.certificate_type} - {document_id}")
    pdf.setStrokeColor(colors.HexColor("#2563EB")); pdf.setLineWidth(2); pdf.rect(14*mm,14*mm,width-28*mm,height-28*mm)
    pdf.setFillColor(colors.HexColor("#0B1120")); pdf.setFont("Helvetica-Bold",17); pdf.drawCentredString(width/2,height-29*mm,"GOVERNMENT DOCUMENT MANAGEMENT SYSTEM")
    pdf.setFillColor(colors.HexColor("#2563EB")); pdf.setFont("Helvetica-Bold",10); pdf.drawCentredString(width/2,height-36*mm,"DEPARTMENT OF CITIZEN SERVICES")
    pdf.setStrokeColor(colors.HexColor("#64748B")); pdf.rect(18*mm,height-55*mm,24*mm,16*mm)
    pdf.setFillColor(colors.HexColor("#475569")); pdf.setFont("Helvetica",7); pdf.drawCentredString(30*mm,height-47*mm,"GOVERNMENT"); pdf.drawCentredString(30*mm,height-51*mm,"LOGO")
    pdf.setFillColor(colors.HexColor("#0B1120")); pdf.setFont("Helvetica-Bold",20); pdf.drawCentredString(width/2,height-66*mm,application.certificate_type.upper())
    pdf.setFont("Helvetica",9); pdf.drawCentredString(width/2,height-73*mm,f"Certificate No: CERT-{issued_at:%Y%m%d}-{application.application_id:06d}")
    x, y = 28*mm, height-94*mm
    for label, value in [("Document ID:", document_id),("Citizen Name:",application.citizen.full_name),("Application ID:",application.reference_number)]:
        pdf.setFont("Helvetica-Bold",10); pdf.drawString(x,y,label); pdf.setFont("Helvetica",10); pdf.drawString(x+35*mm,y,value); y -= 10*mm
    y -= 10*mm; content = f"This is to certify that the application submitted by {application.citizen.full_name} has been reviewed and approved by the Department of Citizen Services. This {application.certificate_type.lower()} is issued for official purposes."
    pdf.setFont("Helvetica",11); line=""
    for word in content.split():
        trial=f"{line} {word}".strip()
        if stringWidth(trial,"Helvetica",11)>width-56*mm: pdf.drawString(x,y,line); y-=7*mm; line=word
        else: line=trial
    pdf.drawString(x,y,line)
    pdf.setFont("Helvetica",9); pdf.drawString(x,57*mm,f"Issue Date: {issued_at:%d %B %Y}"); pdf.drawRightString(width-28*mm,57*mm,f"Authorized by: {administrator.name}")
    pdf.setStrokeColor(colors.HexColor("#475569")); pdf.line(width-82*mm,39*mm,width-28*mm,39*mm); pdf.setFont("Helvetica",8); pdf.drawRightString(width-28*mm,34*mm,"Authorized Signature")
    pdf.drawImage(str(qr_path),28*mm,22*mm,width=28*mm,height=28*mm,mask="auto"); pdf.setFont("Helvetica",7); pdf.drawString(28*mm,18*mm,"Scan to verify this certificate")
    pdf.save(); return issued_at

def _image_to_pdf(image_path: Path, output_path: Path):
    """Convert an image file to a single-page PDF."""
    img = PilImage.open(image_path).convert("RGB")
    img.save(str(output_path), "PDF", resolution=150)

def _merge_uploaded_and_verification(upload_path: Path, verification_pdf: Path, output_path: Path):
    """Merge uploaded document (page 1) with verification page (page 2)."""
    writer = PdfWriter()
    suffix = upload_path.suffix.lower()
    if suffix == ".pdf":
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
    """Generate one final QR-embedded PDF, then hash its exact bytes."""
    if application.certificate: return application.certificate
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
    certificate = Certificate(application=application, document_id=document_id, pdf_path=output.name, qr_path=qr_path.name, issued_by=administrator, issued_date=issued_at, issuance_state="Blockchain Registration Pending")
    certificate.sha256_hash = calculate_file_sha256(output)
    db.session.add(certificate)
    return certificate

def issue_certificate(application, administrator):
    """Persist a pending state before Fabric; issue only after a committed response."""
    certificate=prepare_final_certificate(application,administrator)
    if certificate.issuance_state == "Issued": return certificate
    application.status="Issuance Pending"; certificate.issuance_state="Blockchain Registration Pending"; certificate.issuance_attempts=(certificate.issuance_attempts or 0)+1; certificate.blockchain_error=None
    db.session.commit()
    try:
        result=register_certificate(certificate,administrator); record=result["record"]
        if record["sha256Hash"] != certificate.sha256_hash: raise CertificateIssuanceError("Document ID already exists with a different hash on Fabric.")
        certificate.blockchain_transaction_id=record.get("transactionId") or result.get("transactionId"); certificate.blockchain_registered_at=datetime.now(timezone.utc); certificate.issuance_state="Issued"; certificate.blockchain_error=None; application.status="Issued"; db.session.commit(); return certificate
    except (FabricUnavailable,FabricGatewayError,CertificateIssuanceError) as error:
        db.session.rollback(); certificate=Certificate.query.filter_by(application_id=application.application_id).first(); certificate.issuance_state="Issuance Failed"; certificate.blockchain_error=str(error)[:2000]; certificate.application.status="Issuance Failed"; db.session.commit(); raise CertificateIssuanceError(str(error)) from error

def reconcile_certificate(certificate):
    record=get_certificate(certificate.document_id)["record"]
    if record["sha256Hash"] != certificate.sha256_hash: raise CertificateIssuanceError("Existing Fabric record hash differs from the finalized PDF.")
    certificate.blockchain_transaction_id=record.get("transactionId"); certificate.blockchain_registered_at=datetime.now(timezone.utc); certificate.issuance_state="Issued"; certificate.blockchain_error=None; certificate.application.status="Issued"; db.session.commit(); return certificate

def certificate_verification_url(certificate): return verification_url(certificate.document_id)
