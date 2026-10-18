"""Hash final certificate files; never derive a digest from metadata."""
from __future__ import annotations
import hashlib
from pathlib import Path

class CertificateHashError(RuntimeError):
    pass

def calculate_file_sha256(path: str | Path) -> str:
    """Return the lower-case SHA-256 hex digest for the exact file bytes."""
    file_path = Path(path)
    if not file_path.is_file():
        raise CertificateHashError("Certificate PDF is missing or is not a regular file.")
    digest = hashlib.sha256()
    try:
        with file_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise CertificateHashError("Certificate PDF could not be read.") from error
    return digest.hexdigest()
