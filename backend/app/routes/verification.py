import re
from pathlib import Path

from flask import Blueprint, current_app, flash, render_template, request
from pypdf import PdfReader

from ..extensions import db, limiter
from ..models import Certificate, VerificationLog
from ..services.fabric_gateway_service import FabricGatewayError, FabricUnavailable, get_certificate, verify_certificate
from ..services.hashing_service import CertificateHashError, calculate_file_sha256

verification_bp = Blueprint("verification", __name__, url_prefix="/verify")
DOCUMENT_ID_RE = re.compile(r"^GOV-[A-Z0-9]+-\d{8}-[A-F0-9]{8}$")

def _client_ip():
    return request.remote_addr

def _log(document_id, result):
    db.session.add(VerificationLog(document_id=document_id or "UNKNOWN", result=result, ip_address=_client_ip()))
    db.session.commit()

def _public_record(record):
    return {key: record.get(key) for key in ("documentId", "certificateType", "issuer", "issuedAt", "status", "transactionId")}

@verification_bp.route("", methods=["GET", "POST"])
@limiter.limit("30 per minute")
def verify_form():
    result = None
    if request.method == "POST":
        document_id = request.form.get("document_id", "").strip().upper()
        uploaded = request.files.get("certificate_pdf")
        if not DOCUMENT_ID_RE.fullmatch(document_id):
            flash("Enter a valid certificate document ID.", "error")
        elif not uploaded or not uploaded.filename:
            flash("Select a certificate PDF to check its integrity.", "error")
        elif not uploaded.filename.lower().endswith(".pdf"):
            flash("Only PDF files are accepted for integrity verification.", "error")
        else:
            data = uploaded.read(current_app.config["MAX_VERIFICATION_PDF_SIZE"] + 1)
            if len(data) > current_app.config["MAX_VERIFICATION_PDF_SIZE"] or not data.startswith(b"%PDF-"):
                flash("Upload a readable PDF no larger than 5 MB.", "error")
            else:
                try:
                    import io
                    PdfReader(io.BytesIO(data)).pages
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
                        temporary.write(data); temporary_path = Path(temporary.name)
                    try: uploaded_hash = calculate_file_sha256(temporary_path)
                    finally: temporary_path.unlink(missing_ok=True)
                    gateway = verify_certificate(document_id, uploaded_hash)
                    record = gateway["record"]
                    valid = gateway.get("hashMatches") and record.get("status") == "Active"
                    result = {"outcome": "Verified" if valid else "Integrity verification failed", "message": "The uploaded PDF matches the active certificate registered on Hyperledger Fabric." if valid else "The uploaded PDF does not match an active registered certificate.", "record": _public_record(record)}
                    _log(document_id, "Verified" if valid else "Hash mismatch")
                except (FabricUnavailable, FabricGatewayError):
                    result = {"outcome": "Verification temporarily unavailable", "message": "The Fabric verification service is unavailable. Please try again.", "record": None}; _log(document_id, "Service unavailable")
                except (CertificateHashError, Exception) as error:
                    if error.__class__.__name__ in {"PdfReadError", "EmptyFileError"}:
                        flash("The uploaded file is not a readable PDF.", "error")
                    else: raise
    return render_template("verification/verify.html", result=result)

@verification_bp.get("/<document_id>")
@limiter.limit("60 per minute")
def verify_document(document_id):
    document_id = document_id.upper()
    result = None
    if not DOCUMENT_ID_RE.fullmatch(document_id):
        flash("The verification link contains an invalid document ID.", "error")
    else:
        try:
            record = get_certificate(document_id)["record"]
            status = record.get("status")
            result = {"outcome": "Certificate record found" if status == "Active" else "Certificate revoked", "message": "Upload the PDF below to verify file integrity." if status == "Active" else "This certificate is not active.", "record": _public_record(record)}
            _log(document_id, "Record found" if status == "Active" else "Revoked")
        except FabricGatewayError:
            result = {"outcome": "Certificate not found", "message": "No matching blockchain certificate record was found.", "record": None}; _log(document_id, "Not found")
        except FabricUnavailable:
            result = {"outcome": "Verification temporarily unavailable", "message": "The Fabric verification service is unavailable. Please try again.", "record": None}; _log(document_id, "Service unavailable")
    return render_template("verification/verify.html", result=result, document_id=document_id)
