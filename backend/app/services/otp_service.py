import secrets
from datetime import datetime, timedelta, timezone

from flask import session

OTP_TTL_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_registration_otp(email):
    otp = f"{secrets.randbelow(1_000_000):06d}"
    generated_at = datetime.now(timezone.utc)
    session["registration_otp"] = {"value": otp, "email": email, "generated_at": generated_at.isoformat(), "expires_at": (generated_at + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()}
    return otp


def resend_cooldown_remaining(email):
    record = session.get("registration_otp")
    if not record or record.get("email") != email or not record.get("generated_at"):
        return 0
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(record["generated_at"])).total_seconds()
    return max(0, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed))


def verify_registration_otp(email, submitted_otp):
    record = session.get("registration_otp")
    if not record or record["email"] != email:
        return False
    if datetime.now(timezone.utc) > datetime.fromisoformat(record["expires_at"]):
        session.pop("registration_otp", None)
        return False
    return secrets.compare_digest(record["value"], submitted_otp)

