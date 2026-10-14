import secrets
from datetime import datetime, timedelta, timezone

from flask import session

OTP_TTL_MINUTES = 10


def generate_registration_otp(email):
    otp = f"{secrets.randbelow(1_000_000):06d}"
    session["registration_otp"] = {"value": otp, "email": email, "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)).isoformat()}
    return otp


def verify_registration_otp(email, submitted_otp):
    record = session.get("registration_otp")
    if not record or record["email"] != email:
        return False
    if datetime.now(timezone.utc) > datetime.fromisoformat(record["expires_at"]):
        session.pop("registration_otp", None)
        return False
    return secrets.compare_digest(record["value"], submitted_otp)

