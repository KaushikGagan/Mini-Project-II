import tempfile
from pathlib import Path
import pytest
from backend.app import create_app
from backend.app.extensions import db

@pytest.fixture()
def app():
    root = Path(tempfile.mkdtemp())
    class TestConfig:
        TESTING = True; SECRET_KEY = "test-secret"; SQLALCHEMY_DATABASE_URI = "sqlite://"
        SQLALCHEMY_TRACK_MODIFICATIONS = False; UPLOAD_FOLDER = str(root / "uploads")
        GENERATED_CERTIFICATES_FOLDER = str(root / "certificates"); MAX_CONTENT_LENGTH = 16 * 1024 * 1024
        MAX_DOCUMENT_SIZE = 5 * 1024 * 1024; MAX_VERIFICATION_PDF_SIZE = 5 * 1024 * 1024
        ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}; SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = "Lax"; SESSION_COOKIE_SECURE = False; WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False; RATELIMIT_STORAGE_URI = "memory://"; RATELIMIT_DEFAULT = "200 per day"
        VERIFICATION_BASE_URL = "http://localhost:5000"; FABRIC_GATEWAY_URL = "http://gateway.invalid"; FABRIC_GATEWAY_TOKEN = "test"; FABRIC_GATEWAY_TIMEOUT_SECONDS = 1
        MAIL_SERVER = "localhost"; MAIL_PORT = 25; MAIL_USE_TLS = False; MAIL_USERNAME = MAIL_PASSWORD = MAIL_DEFAULT_SENDER = None
        @classmethod
        def validate(cls): pass
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove(); db.drop_all()
