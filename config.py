import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = str(BASE_DIR / "backend" / "uploads")
    GENERATED_CERTIFICATES_FOLDER = str(BASE_DIR / "backend" / "generated_certificates")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    VERIFICATION_BASE_URL = os.getenv("VERIFICATION_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    MAX_VERIFICATION_PDF_SIZE = int(os.getenv("MAX_VERIFICATION_PDF_SIZE", str(5 * 1024 * 1024)))
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    FABRIC_GATEWAY_URL = os.getenv("FABRIC_GATEWAY_URL", "http://127.0.0.1:8081").rstrip("/")
    FABRIC_GATEWAY_TOKEN = os.getenv("GATEWAY_API_TOKEN")
    FABRIC_GATEWAY_TIMEOUT_SECONDS = float(os.getenv("FABRIC_GATEWAY_TIMEOUT_SECONDS", "12"))

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be set in .env")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("DATABASE_URL must be set in .env")

