from pathlib import Path
import qrcode
from flask import current_app

def verification_url(document_id: str) -> str:
    return f"{current_app.config['VERIFICATION_BASE_URL']}/verify/{document_id}"

def create_certificate_qr(document_id: str) -> tuple[Path, str]:
    url = verification_url(document_id)
    target = Path(current_app.config["GENERATED_CERTIFICATES_FOLDER"]) / f"qr_{document_id}.png"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=(13, 33, 55), back_color=(255, 253, 245))
    img.save(target)
    return target, url
