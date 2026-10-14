from datetime import datetime, timezone

from ..extensions import db


class VerificationLog(db.Model):
    __tablename__ = "verification_logs"
    verification_log_id = db.Column(db.Integer, primary_key=True)
    verification_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    result = db.Column(db.String(32), nullable=False, index=True)
    document_id = db.Column(db.String(64), nullable=False, index=True)

