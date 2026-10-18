from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy import String, cast, or_

from ..extensions import db
from ..models import Administrator, Application, ApplicationDocument, AuditLog, Certificate, Citizen
from ..services.audit_service import write_audit
from ..services.certificate_service import CertificateIssuanceError, issue_certificate as issue_cert, reconcile_certificate as reconcile_cert
from ..services.email_service import send_issuance_email, send_rejection_email, send_revocation_email
from ..services.fabric_gateway_service import FabricGatewayError, FabricUnavailable, update_certificate_status
from ..utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
REVIEWABLE_STATUSES = {"Submitted", "Under Review", "Corrections Requested", "Approved", "Rejected"}


def _current_admin():
    return Administrator.query.get_or_404(session["admin_id"])


@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    admin = _current_admin()
    statistics = {"citizens": Citizen.query.count(), "applications": Application.query.count(), "pending": Application.query.filter(Application.status.in_(["Submitted", "Under Review", "Corrections Requested"])).count(), "approved": Application.query.filter_by(status="Approved").count(), "rejected": Application.query.filter_by(status="Rejected").count(), "issued": Certificate.query.count()}
    return render_template("admin/dashboard.html", admin=admin, statistics=statistics, activities=AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all())


@admin_bp.get("/applications")
@admin_required
def applications():
    query = Application.query.join(Citizen)
    search, status = request.args.get("search", "").strip(), request.args.get("status", "").strip()
    certificate_type, date_value = request.args.get("certificate_type", "").strip(), request.args.get("date", "").strip()
    if search:
        query = query.filter(or_(Citizen.full_name.ilike(f"%{search}%"), Citizen.aadhaar_number.ilike(f"%{search}%"), Application.reference_number.ilike(f"%{search}%"), cast(Application.application_id, String).ilike(f"%{search}%"), Application.certificate_type.ilike(f"%{search}%")))
    if status: query = query.filter(Application.status == status)
    if certificate_type: query = query.filter(Application.certificate_type == certificate_type)
    if date_value:
        try: query = query.filter(db.func.date(Application.submission_date) == datetime.strptime(date_value, "%Y-%m-%d").date())
        except ValueError: flash("Use a valid submission date.", "error")
    order = Application.submission_date.asc() if request.args.get("sort") == "oldest" else Application.submission_date.desc()
    pagination = db.paginate(query.order_by(order), page=request.args.get("page", 1, type=int), per_page=10, error_out=False)
    types = [row[0] for row in db.session.query(Application.certificate_type).distinct().order_by(Application.certificate_type)]
    return render_template("admin/applications.html", applications=pagination, certificate_types=types, filters=request.args)


@admin_bp.get("/applications/<reference_number>")
@admin_required
def application_detail(reference_number):
    application = Application.query.filter_by(reference_number=reference_number).first_or_404()
    write_audit(f"Application {reference_number} viewed", f"Admin: {_current_admin().employee_id}")
    db.session.commit()
    logs = AuditLog.query.filter(AuditLog.action.ilike(f"%{reference_number}%")).order_by(AuditLog.timestamp.desc()).all()
    return render_template("admin/application_detail.html", application=application, logs=logs, statuses=REVIEWABLE_STATUSES)


@admin_bp.post("/applications/<reference_number>/review")
@admin_required
def review_application(reference_number):
    application, administrator = Application.query.filter_by(reference_number=reference_number).first_or_404(), _current_admin()
    status, remarks = request.form.get("status", ""), request.form.get("remarks", "").strip()
    if status not in REVIEWABLE_STATUSES or (status in {"Rejected", "Corrections Requested"} and not remarks):
        flash("Choose a valid status. Remarks are required for rejection or corrections.", "error")
        return redirect(url_for("admin.application_detail", reference_number=reference_number))
    previous = application.status
    application.status, application.remarks, application.reviewed_at, application.reviewed_by = status, remarks, datetime.now(timezone.utc), administrator
    if previous != status: write_audit(f"Application {reference_number} status changed: {previous} → {status}", f"Admin: {administrator.employee_id}")
    if remarks: write_audit(f"Remarks added to application {reference_number}", f"Admin: {administrator.employee_id}")
    db.session.commit()
    if status in {"Rejected", "Corrections Requested"}: send_rejection_email(application)
    flash("Application review saved.", "success")
    return redirect(url_for("admin.application_detail", reference_number=reference_number))


@admin_bp.post("/applications/<reference_number>/issue")
@admin_required
def issue_certificate_route(reference_number):
    application = Application.query.filter_by(reference_number=reference_number).first_or_404()
    if application.status not in {"Approved", "Issuance Failed", "Issued"}:
        flash("Only approved applications can receive certificates.", "error")
    else:
        try:
            if application.certificate and application.certificate.issuance_state == "Issuance Failed":
                try:
                    certificate = reconcile_cert(application.certificate)
                except FabricGatewayError:
                    certificate = issue_cert(application, _current_admin())
            else:
                certificate = issue_cert(application, _current_admin())
            write_audit(f"Certificate {certificate.document_id} issued and registered on Fabric for application {reference_number}", f"Admin: {_current_admin().employee_id}")
            db.session.commit()
            send_issuance_email(certificate)
            flash("Final certificate was registered on Fabric and is ready for download.", "success")
        except CertificateIssuanceError as error:
            flash(f"Certificate is not issued yet: {error}", "error")
    return redirect(url_for("admin.application_detail", reference_number=reference_number))


@admin_bp.post("/certificates/<document_id>/revoke")
@admin_required
def revoke_certificate(document_id):
    certificate = Certificate.query.filter_by(document_id=document_id).first_or_404()
    if certificate.issuance_state != "Issued":
        flash("Only a Fabric-issued certificate can be revoked.", "error")
    else:
        try:
            update_certificate_status(certificate.document_id, "Revoked")
            certificate.issuance_state = "Revoked"
            certificate.application.status = "Revoked"
            write_audit(f"Certificate {certificate.document_id} revoked on Fabric", f"Admin: {_current_admin().employee_id}")
            db.session.commit()
            send_revocation_email(certificate)
            flash("Certificate was revoked on Fabric.", "success")
        except (FabricUnavailable, FabricGatewayError) as error:
            flash(f"Revocation was not confirmed: {error}", "error")
    return redirect(url_for("admin.application_detail", reference_number=certificate.application.reference_number))


@admin_bp.get("/documents/<int:document_id>/view")
@admin_required
def view_document(document_id):
    document = ApplicationDocument.query.get_or_404(document_id)
    write_audit(f"Supporting document viewed for application {document.application.reference_number}", f"Admin: {_current_admin().employee_id}")
    db.session.commit()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], document.stored_path, as_attachment=False, download_name=document.original_filename)


@admin_bp.get("/certificates/<document_id>/download")
@admin_required
def download_certificate(document_id):
    certificate = Certificate.query.filter_by(document_id=document_id).first_or_404()
    return send_from_directory(current_app.config["GENERATED_CERTIFICATES_FOLDER"], Path(certificate.pdf_path).name, as_attachment=True, download_name=f"{certificate.document_id}.pdf")
