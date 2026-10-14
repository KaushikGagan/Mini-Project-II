from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .mixins import TimestampMixin


class Citizen(TimestampMixin, db.Model):
    __tablename__ = "citizens"
    citizen_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    aadhaar_number = db.Column(db.String(12), nullable=False, unique=True, index=True)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    phone_number = db.Column(db.String(15), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    applications = db.relationship("Application", back_populates="citizen", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

