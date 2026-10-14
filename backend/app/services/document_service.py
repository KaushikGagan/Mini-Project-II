from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import ApplicationDocument

MIME_BY_EXTENSION = {
    "pdf": {"application/pdf"},
    "png": {"image/png"},
    "jpg": {"image/jpeg", "image/jpg"},
    "jpeg": {"image/jpeg", "image/jpg"},
}


def store_application_documents(application, files):
    """Validate every upload before persisting it below the application directory."""
    valid_files = [file for file in files if file and file.filename]
    if not valid_files:
        raise ValueError("Upload at least one supporting document.")

    checked_files = []
    for file in valid_files:
        safe_name = secure_filename(file.filename)
        if not safe_name or "." not in safe_name:
            raise ValueError("Every document must have a valid filename and extension.")
        extension = safe_name.rsplit(".", 1)[1].lower()
        if extension not in current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]:
            raise ValueError("Only PDF, PNG, JPG, and JPEG documents are allowed.")
        supplied_type = (file.mimetype or "").lower()
        if supplied_type and supplied_type not in MIME_BY_EXTENSION[extension]:
            raise ValueError(f"The file type for {safe_name} does not match its extension.")
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size == 0:
            raise ValueError(f"{safe_name} is empty.")
        if size > current_app.config["MAX_DOCUMENT_SIZE"]:
            raise ValueError(f"{safe_name} exceeds the 5 MB per-document limit.")
        checked_files.append((file, safe_name, extension, size))

    relative_directory = Path(application.reference_number)
    storage_directory = Path(current_app.config["UPLOAD_FOLDER"]) / relative_directory
    storage_directory.mkdir(parents=True, exist_ok=True)
    records = []
    for file, safe_name, extension, size in checked_files:
        stored_name = f"{uuid4().hex}_{safe_name}"
        relative_path = relative_directory / stored_name
        file.save(storage_directory / stored_name)
        record = ApplicationDocument(
            application=application,
            original_filename=safe_name,
            stored_path=str(relative_path).replace("\\", "/"),
            mime_type=next(iter(MIME_BY_EXTENSION[extension])),
            file_size=size,
        )
        db.session.add(record)
        records.append(record)
    return records
