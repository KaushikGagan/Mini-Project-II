import re

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from ..extensions import db
from ..models import Administrator, Citizen
from ..services.audit_service import write_audit
from ..services.otp_service import generate_registration_otp, verify_registration_otp

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
AADHAAR_RE = re.compile(r"^[2-9][0-9]{11}$")
PHONE_RE = re.compile(r"^[6-9][0-9]{9}$")


def valid_password(password):
    return len(password) >= 8 and any(char.isupper() for char in password) and any(char.islower() for char in password) and any(char.isdigit() for char in password)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        aadhaar = request.form.get("aadhaar_number", "").replace(" ", "")
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone_number", "").replace(" ", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        otp = request.form.get("otp", "").strip()
        if not full_name or not AADHAAR_RE.fullmatch(aadhaar) or not PHONE_RE.fullmatch(phone):
            flash("Enter a valid name, 12-digit Aadhaar number, and 10-digit Indian phone number.", "error")
        elif "@" not in email:
            flash("Enter a valid email address.", "error")
        elif password != confirm_password or not valid_password(password):
            flash("Passwords must match and contain 8+ characters with uppercase, lowercase, and a number.", "error")
        elif Citizen.query.filter(or_(Citizen.aadhaar_number == aadhaar, Citizen.email == email, Citizen.phone_number == phone)).first():
            flash("An account already exists with this Aadhaar number, email, or phone number.", "error")
        elif not verify_registration_otp(email, otp):
            flash("OTP is invalid or expired. Request a new OTP.", "error")
        else:
            citizen = Citizen(full_name=full_name, aadhaar_number=aadhaar, email=email, phone_number=phone)
            citizen.set_password(password)
            db.session.add(citizen)
            write_audit("Citizen account registered", f"Citizen: {email}")
            db.session.commit()
            session.pop("registration_otp", None)
            flash("Registration complete. You can now sign in.", "success")
            return redirect(url_for("auth.citizen_login"))
    return render_template("auth/register.html")


@auth_bp.post("/request-otp")
def request_otp():
    email = request.form.get("email", "").strip().lower()
    if "@" not in email:
        if request.accept_mimetypes.best == "application/json":
            return jsonify(ok=False, message="Enter a valid email address before requesting an OTP."), 400
        flash("Enter a valid email address before requesting an OTP.", "error")
        return redirect(url_for("auth.register"))
    otp = generate_registration_otp(email)
    # Development-only delivery channel. Production will replace this with email/SMS.
    print(f"\n[DEVELOPMENT OTP] Registration code for {email}: {otp}\n", flush=True)
    current_app.logger.warning("Development registration OTP for %s: %s", email, otp)
    if request.accept_mimetypes.best == "application/json":
        return jsonify(ok=True, message="OTP generated. Check the Flask terminal during development.")
    flash("OTP generated. Check the Flask terminal during development.", "success")
    return redirect(url_for("auth.register"))


@auth_bp.route("/login", methods=["GET", "POST"])
def citizen_login():
    if request.method == "POST":
        citizen = Citizen.query.filter_by(aadhaar_number=request.form.get("aadhaar_number", "").replace(" ", "")).first()
        if citizen and citizen.check_password(request.form.get("password", "")):
            session.clear()
            session["citizen_id"] = citizen.citizen_id
            session["user_type"] = "citizen"
            write_audit("Citizen signed in", f"Citizen: {citizen.email}")
            db.session.commit()
            return redirect(url_for("citizen.dashboard"))
        flash("Invalid Aadhaar number or password.", "error")
    return render_template("auth/citizen_login.html")


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = Administrator.query.filter_by(employee_id=request.form.get("employee_id", "").strip().upper()).first()
        if admin and admin.check_password(request.form.get("password", "")):
            session.clear()
            session["admin_id"] = admin.admin_id
            session["user_type"] = "administrator"
            write_audit("Administrator signed in", f"Admin: {admin.employee_id}")
            db.session.commit()
            return redirect(url_for("admin.dashboard"))
        flash("Invalid employee ID or password.", "error")
    return render_template("auth/admin_login.html")


@auth_bp.post("/logout")
def logout():
    user = session.get("user_type", "user")
    session.clear()
    flash(f"{user.title()} session ended securely.", "success")
    return redirect(url_for("main.index"))
