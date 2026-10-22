# Government Document Management and Verification System

## 1. Project purpose

This project is a government-document workflow application. Citizens create accounts, submit certificate applications and supporting documents, and track their status. Administrators review applications, issue certificates, and revoke certificates when required. A final PDF certificate is protected through SHA-256 hashing, a QR verification URL, and a Hyperledger Fabric certificate record.

## 2. Technology stack

| Area | Technology |
| --- | --- |
| Web application | Python 3.14, Flask |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Authentication | Flask sessions, Werkzeug password hashing, email OTP |
| PDF generation | ReportLab |
| QR generation | `qrcode` and Pillow |
| PDF validation | `pypdf` |
| Blockchain | Hyperledger Fabric 2.5 test network, Docker Desktop, WSL2/Ubuntu |
| Fabric client | Node.js 20 internal gateway using `@hyperledger/fabric-gateway` |
| Smart contract | Go certificate-record chaincode |

## 3. Local environment setup

The development environment uses Windows 11, Docker Desktop, WSL2/Ubuntu, Python, PostgreSQL, Node.js and Hyperledger Fabric.

### Python application

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\flask.exe --app run db upgrade
.\.venv\Scripts\flask.exe run.py
```

The application is available locally at `http://127.0.0.1:5000`.

### Database

PostgreSQL stores user accounts, applications, uploaded-file metadata, certificates, audit activity and verification activity. The project uses Alembic migrations; database tables are not created with `db.create_all()` in normal use.

Applied schema revisions are:

- `e633d85cdeea`: core accounts, applications, certificates, audit and verification tables.
- `4fe49e0e15d7`: application documents and certificate workflow fields.
- `8a0e32d1b5c1`: recoverable issuance state, registration time/error and issuance-attempt count.

## 4. User workflow

1. A citizen registers with name, Aadhaar number, email, phone number and password.
2. The system sends a six-digit OTP by email. The OTP is session-bound, expires after ten minutes and has a resend cooldown.
3. The citizen signs in and submits an application with allowed supporting documents.
4. The system generates an application reference number and records an audit event.
5. An administrator reviews documents and sets a status: Submitted, Under Review, Corrections Requested, Approved or Rejected.
6. An approved application can enter certificate issuance.

## 5. File security and access control

- Passwords are stored as hashes, never plaintext.
- Citizen, administrator and public routes have separate access controls.
- Citizens cannot access another citizen's applications or certificates.
- Supporting documents use secured filenames, extension/MIME/size validation and stored metadata.
- Browser state-changing requests use CSRF protection.
- Public verification is rate limited.
- Environment secrets, uploads, generated certificates, Fabric wallets and gateway environment files are excluded from Git.

## 6. Certificate issuance process

1. The application allocates a unique `GOV-...` document ID.
2. It creates a verification URL using `VERIFICATION_BASE_URL`.
3. It generates a QR code that points to `/verify/<document-id>`.
4. ReportLab embeds the QR code in the final certificate PDF.
5. Python `hashlib` calculates a 64-character SHA-256 digest from the final PDF bytes.
6. PostgreSQL records a durable `Blockchain Registration Pending` state before the external Fabric request.
7. The internal gateway registers document ID, SHA-256 hash, certificate type, issuer and issue timestamp on Fabric.
8. The actual Fabric transaction ID is saved in PostgreSQL.
9. Only a confirmed record becomes `Issued` and available for download.

If blockchain registration fails, the immutable final PDF and hash remain available for safe reconciliation rather than silent regeneration. Relevant states include Blockchain Registration Pending, Issuance Failed, Issued and Revoked.

## 7. Hyperledger Fabric architecture

The Fabric test network uses channel `mychannel`. The dedicated Go chaincode is named `certificate-record`; it is separate from the existing `basic` sample chaincode.

Chaincode operations:

- `Ping`
- `RegisterCertificate`
- `GetCertificate`
- `VerifyCertificate`
- `UpdateCertificateStatus`
- `RevokeCertificate`

No PDF, Aadhaar number, password, private key or supporting document is written to Fabric. Only non-sensitive certificate metadata and the final PDF hash are recorded.

The Node gateway is an internal service. Flask calls its narrow HTTP API; browsers never receive Fabric private keys or administrative credentials.

## 8. Starting the local blockchain services

Start Docker Desktop and enable WSL integration for Ubuntu. Then use Ubuntu:

```bash
docker start orderer.example.com peer0.org1.example.com peer0.org2.example.com

cd ~/fabric-workspace/fabric-samples/test-network
export PATH="${PWD}/../bin:$PATH"
export FABRIC_CFG_PATH="${PWD}/../config"
. scripts/envVar.sh
setGlobals 1

peer chaincode query -C mychannel -n certificate-record -c '{"Args":["Ping"]}'
```

When the query returns `ok`, start the gateway in another Ubuntu terminal:

```bash
cd "/mnt/c/Users/gagan/OneDrive/Desktop/programs and misc/Mini project/fabric-gateway"
source ~/.bashrc
nvm use 20
node --env-file=.env src/server.js
```

The gateway must remain running while the Flask application issues, verifies or revokes certificates.

## 9. Gateway configuration

`fabric-gateway/.env` is local-only. It needs the Org1 MSP ID, administrative signing certificate path, private-key path, TLS certificate path, peer endpoint, host alias, channel, chaincode name and an internal gateway token. Flask `.env` must use the same token and gateway URL.

Never commit `.env`, private keys, Fabric identity folders, generated PDFs, uploaded documents, Gmail App Passwords or real citizen data.

## 10. Public verification

The public verification page is `/verify`.

- A document-ID lookup obtains the public certificate record from Fabric.
- A PDF upload is checked for a valid readable PDF structure and size limit.
- The uploaded file is hashed and compared with the hash registered on Fabric.
- A matching hash plus Active status produces a verified result.
- A copied QR code alone cannot verify a different PDF because the PDF hash must independently match.
- Public results disclose only document ID, type, issuer, issue date, status and transaction ID.

## 11. Testing status

Executed locally:

- Python `pytest`: 4 tests passed.
- Python compilation and Flask route registration passed.
- Database migration head verified as `8a0e32d1b5c1`.
- Go `go test ./...` for `certificate-record` passed.
- Fabric evidence confirmed that `certificate-record` is committed on `mychannel` with approvals from Org1MSP and Org2MSP.

Still required before presenting the complete Fabric workflow:

1. Keep Docker, peers/orderer, gateway and Flask running together.
2. Approve and issue one fresh application.
3. Confirm the Fabric transaction ID is stored locally.
4. Verify the downloaded original PDF publicly.
5. Modify a copy of the PDF and confirm that verification fails.
6. Revoke a certificate and confirm the portal reports it as revoked.

## 12. Fresh database state

Citizen data was deliberately cleared for a fresh test cycle. At the time of cleanup there were zero citizen accounts, applications, certificate records, verification logs, upload files and generated certificate files. The administrator account and schema migrations were retained.

## 13. Deployment guidance

Render can host the Flask application but is not suitable for this full Fabric deployment on its Free tier: Free services sleep after idle time, local files are ephemeral, Free PostgreSQL expires, and the hosted service cannot reach a WSL-local Fabric network.

For a college demonstration, run the complete stack locally and publish only Flask through Cloudflare Tunnel while the laptop is on. For continuous public use, deploy Flask, PostgreSQL, gateway and the Fabric network on persistent private infrastructure such as a properly sized virtual machine; do not expose peer/orderer ports or Fabric identities to the public internet.

## 14. Repository notes

The vendored `fabric-chaincode/certificate-record/vendor/github.com/go-openapi/spec/appveyor.yml` is included in this repository with its build configuration only. Third-party notification credentials were deliberately excluded.
