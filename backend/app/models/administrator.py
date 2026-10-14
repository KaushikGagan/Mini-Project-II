from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .mixins import TimestampMixin


class Administrator(TimestampMixin, db.Model):
    __tablename__ = "administrators"
    admin_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    employee_id = db.Column(db.String(32), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="Administrator")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

