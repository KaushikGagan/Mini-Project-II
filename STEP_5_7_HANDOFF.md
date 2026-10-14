# Developer Handoff — Steps 5–7 Complete

## Scope completed

- **Step 5:** Citizen applications, secure supporting-document upload, search/filter, ownership controls, editable-while-submitted rules, profile updates, application timeline, and issued-certificate downloads.
- **Step 6:** Administrator application search/filter/sort, document previews, review actions, approval/rejection/corrections workflow, and audit logging.
- **Step 7:** ReportLab PDF certificate generation after approval, unique document IDs, local certificate storage, and citizen/admin downloads.

## New/changed folders and services

- `backend/app/models/application_document.py` — uploaded-document metadata.
- `backend/app/services/document_service.py` — extension/MIME/size validation and secure file storage.
- `backend/app/services/certificate_service.py` — official-style ReportLab PDF generator.
- `backend/app/routes/citizen.py` and `admin.py` — full scoped workflows.
- `backend/app/templates/citizen/` and `admin/` — application, review, profile, and certificate pages.
- `backend/uploads/<application-reference>/` stores uploads (Git ignored).
- `backend/generated_certificates/` stores PDFs (Git ignored).

## Database changes

Migration `4fe49e0e15d7` adds:

- `application_documents` table: original name, secured relative path, MIME type, byte size, timestamps.
- Application reference numbers, reviewer foreign key, and review timestamp.
- Certificate issuer foreign key.
- Nullable certificate hash because Step 8 has not started; SHA-256 must not be generated yet.

## New dependency

- `reportlab>=4.2,<5.0`

## Workflow

1. Citizen submits an allowed PDF/PNG/JPG/JPEG supporting document with an application.
2. The app creates a unique `APP-...` reference and status `Submitted`.
3. The citizen can edit only while the status is `Submitted`.
4. Admin reviews documents, changes status, and adds remarks; each action is audited.
5. Only an `Approved` application can receive a PDF certificate.
6. Certificate generation creates a unique `GOV-...` document ID, stores a PDF, and changes status to `Issued`.

## Testing performed

- Real PostgreSQL migration applied.
- Application submission with PDF upload passed.
- Document metadata/path storage passed.
- Cross-citizen application access returned 404.
- Admin approval passed.
- ReportLab PDF generation and file existence passed.
- Citizen certificate download and admin document preview passed.
- Test records and generated test files were removed.

## Remaining roadmap

Steps 8–12 remain unimplemented: SHA-256 hashing, Hyperledger Fabric gateway integration, QR generation, public verification, and final testing/deployment. Do not begin Step 8 without explicit instruction.
