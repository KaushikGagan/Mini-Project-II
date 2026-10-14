# Developer Handoff — Phases 1–3 Complete

## Project structure

```text
backend/app/
  blockchain/       Reserved for the later Fabric gateway integration
  models/           SQLAlchemy models and relationships
  routes/           Flask Blueprints for public, authentication, citizen, and admin views
  services/         OTP and audit-log services
  static/           Premium dark-theme CSS, JavaScript, and images
  templates/        Jinja base, public, auth, dashboard, and error templates
  utils/            Route-access decorators
backend/uploads/    Ignored future supporting-document storage
backend/generated_certificates/ Ignored future certificate storage
migrations/         Alembic migration history
```

## Installed packages

- Flask 3.1.3
- Flask-SQLAlchemy 3.1.1
- Flask-Migrate 4.1.0 / Alembic 1.19.1
- psycopg 3.3.4 (PostgreSQL driver)
- python-dotenv 1.2.3
- email-validator 2.3.0

Python is run in `.venv` using Python 3.14. PostgreSQL 18.6 is installed locally and the project database is `gov_document_management`.

## Database schema

Alembic revision `e633d85cdeea` creates these tables:

- `citizens`: unique Aadhaar number, email, phone number, password hash, timestamps.
- `administrators`: unique email and employee ID, password hash, role, timestamps.
- `applications`: belongs to a citizen; certificate type, status, submission date, remarks, timestamps.
- `certificates`: one-to-one with an application; unique document ID and SHA-256 hash; future QR, PDF, and Fabric transaction references.
- `verification_logs`: document ID, verification result, IP address, and timestamp.
- `audit_logs`: action, actor, and timestamp.

Foreign keys enforce application-to-citizen and certificate-to-application ownership. Frequently queried identifiers and statuses are indexed.

## Routes

| Route | Purpose |
| --- | --- |
| `GET /` | Public landing page |
| `GET/POST /auth/register` | Citizen registration and OTP verification |
| `POST /auth/request-otp` | Generate a development OTP (printed to server terminal) |
| `GET/POST /auth/login` | Citizen login with Aadhaar number and password |
| `GET/POST /auth/admin/login` | Administrator login with employee ID and password |
| `POST /auth/logout` | Securely clear the session |
| `GET /citizen/dashboard` | Citizen-protected dashboard with live application counts |
| `GET /admin/dashboard` | Administrator-protected dashboard with live counts and audit activity |

## Authentication flow

1. Registration validates full name, 12-digit Aadhaar number, email, Indian phone number, and password strength.
2. `/auth/request-otp` creates a cryptographically random six-digit OTP tied to the email and stored in Flask’s signed session for 10 minutes. In development it is logged to the Flask terminal only.
3. Validated citizens are stored in PostgreSQL with a Werkzeug-generated password hash. Aadhaar, email, and phone duplicate constraints are enforced in both code and database.
4. Login checks the hash, clears any prior session, records the appropriate user ID/type, and writes an audit record.
5. Access decorators protect citizen and administrator dashboards separately.

## Verification completed

- Flask starts and homepage returns HTTP 200.
- PostgreSQL 18.6 connection verified.
- Database created and all six tables generated through Alembic migration.
- Citizen OTP registration, password hashing, duplicate-safe persistence, login, signed session, and dashboard verified.
- Administrator password authentication, session, and dashboard verified.
- Application, certificate, verification-log, and audit-log CRUD/relationships verified.
- Test records were removed after verification.

## Run instructions

```powershell
.\.venv\Scripts\Activate.ps1
flask --app run create-admin
python run.py
```

Copy `.env.example` to `.env` on another machine and provide its own `SECRET_KEY` and PostgreSQL `DATABASE_URL`. Never commit `.env`, uploads, generated certificates, real user data, or Fabric credentials.

## Current progress and next phase

Phases 1–3 are complete. Phase 4 should implement the actual citizen document-application form and secure supporting-document uploads, followed by administrator review/approval workflow. Certificate PDF, QR code, SHA-256 hashing, and Hyperledger Fabric gateway integration must remain a later phase as requested.
