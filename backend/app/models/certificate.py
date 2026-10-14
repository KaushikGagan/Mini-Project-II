from datetime import datetime, timezone

from ..extensions import db
from .mixins import TimestampMixin


class Certificate(TimestampMixin, db.Model):
    __tablename__ = "certificates"
    certificate_id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    document_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    # Hashing is intentionally deferred to roadmap Step 8.
    sha256_hash = db.Column(db.String(64), unique=True, index=True)
    qr_path = db.Column(db.String(512))
    pdf_path = db.Column(db.String(512))
    blockchain_transaction_id = db.Column(db.String(256), unique=True)
    issued_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    issued_by_admin_id = db.Column(db.Integer, db.ForeignKey("administrators.admin_id", ondelete="SET NULL"), index=True)
    application = db.relationship("Application", back_populates="certificate")
    issued_by = db.relationship("Administrator", foreign_keys=[issued_by_admin_id])

