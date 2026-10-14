from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from sqlalchemy import or_

from ..extensions import db
from ..models import Application, Certificate, Citizen
from ..services.audit_service import write_audit
from ..services.document_service import store_application_documents
from ..utils.decorators import citizen_required

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")
CERTIFICATE_TYPES = ("Birth Certificate", "Death Certificate", "Marriage Certificate", "Income Certificate", "Income and Asset Certificate (EWS)", "Residence Certificate", "Domicile / Nativity Certificate", "Caste / Community Certificate", "Disability Certificate", "Character Certificate", "Legal Heir Certificate", "Family Membership Certificate", "Minority Certificate", "Class 10 Mark Sheet / Passing Certificate", "Class 12 Mark Sheet / Passing Certificate", "Migration Certificate", "Equivalency Certificate", "Eligibility Certificate")


def _current_citizen():
    return Citizen.query.get_or_404(session["citizen_id"])


def _owned_application(reference_number):
    application = Application.query.filter_by(reference_number=reference_number, citizen_id=session["citizen_id"]).first()
    if not application:
        abort(404)
    return application


@citizen_bp.get("/dashboard")
@citizen_required
def dashboard():
    citizen = _current_citizen()
    applications = citizen.applications.order_by(Application.submission_date.desc()).all()
    statistics = {"total": len(applications), "pending": sum(item.status in {"Submitted", "Under Review", "Corrections Requested"} for item in applications), "approved": sum(item.status == "Approved" for item in applications), "rejected": sum(item.status == "Rejected" for item in applications), "issued": sum(item.status == "Issued" for item in applications)}
    return render_template("citizen/dashboard.html", citizen=citizen, applications=applications[:5], statistics=statistics)


@citizen_bp.route("/applications", methods=["GET", "POST"])
@citizen_required
def applications():
    citizen = _current_citizen()
    if request.method == "POST":
        certificate_type, remarks = request.form.get("certificate_type", ""), request.form.get("remarks", "").strip()
        if certificate_type not in CERTIFICATE_TYPES:
            flash("Choose a supported certificate type.", "error")
        else:
            application = Application(citizen=citizen, certificate_type=certificate_type, remarks=remarks)
            db.session.add(application)
            db.session.flush()
            try:
                store_application_documents(application, request.files.getlist("supporting_documents"))
            except ValueError as error:
                db.session.rollback()
                flash(str(error), "error")
            else:
                write_audit(f"Application {application.reference_number} submitted", f"Citizen: {citizen.email}")
                db.session.commit()
                flash("Your application was submitted successfully.", "success")
                return redirect(url_for("citizen.application_detail", reference_number=application.reference_number))
    query = Application.query.filter_by(citizen_id=citizen.citizen_id)
    search, status = request.args.get("search", "").strip(), request.args.get("status", "").strip()
    if search:
        query = query.filter(or_(Application.reference_number.ilike(f"%{search}%"), Application.certificate_type.ilike(f"%{search}%")))
    if status:
        query = query.filter_by(status=status)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(query.order_by(Application.submission_date.desc()), page=page, per_page=8, error_out=False)
    return render_template("citizen/applications.html", certificate_types=CERTIFICATE_TYPES, applications=pagination, search=search, selected_status=status)


@citizen_bp.route("/applications/<reference_number>", methods=["GET", "POST"])
@citizen_required
def application_detail(reference_number):
    application = _owned_application(reference_number)
    if request.method == "POST":
        if application.status != "Submitted":
            flash("This application can no longer be edited after review begins.", "error")
            return redirect(url_for("citizen.application_detail", reference_number=reference_number))
        certificate_type = request.form.get("certificate_type", "")
        if certificate_type not in CERTIFICATE_TYPES:
            flash("Choose a supported certificate type.", "error")
            return redirect(url_for("citizen.application_detail", reference_number=reference_number))
        application.certificate_type, application.remarks = certificate_type, request.form.get("remarks", "").strip()
        uploads = request.files.getlist("supporting_documents")
        if any(item and item.filename for item in uploads):
            try:
                store_application_documents(application, uploads)
            except ValueError as error:
                db.session.rollback()
                flash(str(error), "error")
                return redirect(url_for("citizen.application_detail", reference_number=reference_number))
        write_audit(f"Application {application.reference_number} updated", f"Citizen: {application.citizen.email}")
        db.session.commit()
        flash("Application updated.", "success")
        return redirect(url_for("citizen.application_detail", reference_number=reference_number))
    events = [(application.submission_date, "Submitted", "Application submitted by citizen.")]
    if application.reviewed_at:
        events.append((application.reviewed_at, application.status, f"Last reviewed by {application.reviewed_by.name if application.reviewed_by else 'an administrator'}."))
    if application.certificate:
        events.append((application.certificate.issued_date, "Issued", "Official certificate generated."))
    return render_template("citizen/application_detail.html", application=application, certificate_types=CERTIFICATE_TYPES, events=sorted(events, key=lambda event: event[0]))


@citizen_bp.route("/profile", methods=["GET", "POST"])
@citizen_required
def profile():
    citizen = _current_citizen()
    if request.method == "POST":
        full_name, email, phone = request.form.get("full_name", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("phone_number", "").strip()
        existing = Citizen.query.filter(Citizen.citizen_id != citizen.citizen_id, or_(Citizen.email == email, Citizen.phone_number == phone)).first()
        if not full_name or "@" not in email or not phone.isdigit() or len(phone) != 10 or existing:
            flash("Enter valid profile details. Email and phone must be unique.", "error")
        else:
            citizen.full_name, citizen.email, citizen.phone_number = full_name, email, phone
            write_audit("Citizen profile updated", f"Citizen: {citizen.email}")
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("citizen.profile"))
    return render_template("citizen/profile.html", citizen=citizen)


@citizen_bp.get("/certificates")
@citizen_required
def certificates():
    rows = Certificate.query.join(Application).filter(Application.citizen_id == session["citizen_id"], Application.status == "Issued").order_by(Certificate.issued_date.desc()).all()
    return render_template("citizen/certificates.html", certificates=rows)


@citizen_bp.get("/certificates/<document_id>/download")
@citizen_required
def download_certificate(document_id):
    certificate = Certificate.query.join(Application).filter(Certificate.document_id == document_id, Application.citizen_id == session["citizen_id"], Application.status == "Issued").first_or_404()
    return send_from_directory(current_app.config["GENERATED_CERTIFICATES_FOLDER"], Path(certificate.pdf_path).name, as_attachment=True, download_name=f"{certificate.document_id}.pdf")
