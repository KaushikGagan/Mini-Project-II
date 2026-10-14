from datetime import datetime, timezone

from ..extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    audit_log_id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    performed_by = db.Column(db.String(150), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

