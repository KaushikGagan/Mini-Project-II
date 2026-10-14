from datetime import datetime, timezone
from uuid import uuid4

from ..extensions import db
from .mixins import TimestampMixin


class Application(TimestampMixin, db.Model):
    __tablename__ = "applications"
    application_id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(32), nullable=False, unique=True, index=True, default=lambda: f"APP-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}")
    citizen_id = db.Column(db.Integer, db.ForeignKey("citizens.citizen_id", ondelete="CASCADE"), nullable=False, index=True)
    certificate_type = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(40), nullable=False, default="Submitted", index=True)
    submission_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    remarks = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime(timezone=True))
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey("administrators.admin_id", ondelete="SET NULL"), index=True)
    citizen = db.relationship("Citizen", back_populates="applications")
    certificate = db.relationship("Certificate", back_populates="application", uselist=False, cascade="all, delete-orphan")
    documents = db.relationship("ApplicationDocument", back_populates="application", lazy="dynamic", cascade="all, delete-orphan")
    reviewed_by = db.relationship("Administrator", foreign_keys=[reviewed_by_admin_id])

