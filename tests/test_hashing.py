import pytest
from backend.app.services.hashing_service import CertificateHashError, calculate_file_sha256

def test_identical_contents_have_identical_hashes(tmp_path):
    one, two = tmp_path / "one.pdf", tmp_path / "two.pdf"
    one.write_bytes(b"%PDF-1.4\ncontent"); two.write_bytes(b"%PDF-1.4\ncontent")
    assert calculate_file_sha256(one) == calculate_file_sha256(two)
    assert len(calculate_file_sha256(one)) == 64

def test_changed_contents_have_different_hashes(tmp_path):
    source = tmp_path / "certificate.pdf"; source.write_bytes(b"first")
    initial = calculate_file_sha256(source); source.write_bytes(b"second")
    assert initial != calculate_file_sha256(source)

def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(CertificateHashError): calculate_file_sha256(tmp_path / "missing.pdf")
