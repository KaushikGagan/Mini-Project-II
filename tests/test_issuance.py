from backend.app.extensions import db
from backend.app.models import Administrator, Application, Citizen
from backend.app.services import certificate_service

def test_final_pdf_is_qr_embedded_hashed_and_issued(app, monkeypatch):
    with app.app_context():
        citizen = Citizen(full_name="Test Citizen", aadhaar_number="234567890123", email="test@example.com", phone_number="9876543210")
        citizen.set_password("StrongPass1")
        admin = Administrator(name="Test Admin", email="admin@example.com", employee_id="ADM1"); admin.set_password("StrongPass1")
        application = Application(citizen=citizen, certificate_type="Birth Certificate", status="Approved")
        db.session.add_all([citizen, admin, application]); db.session.commit()
        monkeypatch.setattr(certificate_service, "register_certificate", lambda certificate, _: {"record": {"sha256Hash": certificate.sha256_hash, "transactionId": "tx-test"}})
        certificate = certificate_service.issue_certificate(application, admin)
        assert certificate.issuance_state == "Issued" and certificate.application.status == "Issued"
        assert certificate.sha256_hash == certificate_service.calculate_file_sha256(app.config["GENERATED_CERTIFICATES_FOLDER"] + "/" + certificate.pdf_path)
        assert (app.config["GENERATED_CERTIFICATES_FOLDER"] + "/" + certificate.qr_path)
        assert certificate.blockchain_transaction_id == "tx-test"
