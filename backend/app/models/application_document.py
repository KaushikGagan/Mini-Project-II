from ..extensions import db
from .mixins import TimestampMixin


class ApplicationDocument(TimestampMixin, db.Model):
    __tablename__ = "application_documents"

    document_id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("applications.application_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(512), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)

    application = db.relationship("Application", back_populates="documents")
