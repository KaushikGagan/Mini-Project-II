from pathlib import Path
import qrcode
from flask import current_app

def verification_url(document_id: str) -> str:
    return f"{current_app.config['VERIFICATION_BASE_URL']}/verify/{document_id}"

def create_certificate_qr(document_id: str) -> tuple[Path, str]:
    url = verification_url(document_id)
    target = Path(current_app.config["GENERATED_CERTIFICATES_FOLDER"]) / f"qr_{document_id}.png"
    qrcode.make(url).save(target)
    return target, url
