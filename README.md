# Government Document Management and Verification System

Flask/PostgreSQL application that issues QR-embedded PDFs, hashes their final bytes, and registers hashes on Hyperledger Fabric through a private local gateway.

## Local setup

Install Python 3.14, PostgreSQL 18+, Node.js 20+, Docker Desktop, WSL2 and Fabric 2.5.x. Copy `.env.example` to `.env` and set all real secrets locally.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\flask.exe --app run db upgrade
.\.venv\Scripts\flask.exe --app run create-admin
.\.venv\Scripts\python.exe run.py
```

Public verification is at `http://127.0.0.1:5000/verify`.

## Issuance process

The app allocates a document ID, generates a QR URL from `VERIFICATION_BASE_URL`, embeds it in the final PDF, calculates SHA-256 from the final bytes, stores a durable pending state, and only marks the certificate **Issued** after Fabric confirms registration. Failed calls leave an immutable PDF/hash in **Issuance Failed** for safe reconciliation/retry.

## Fabric deployment in WSL

Do not run `network.sh down`. Keep the existing sample chaincode. From the current Fabric samples test network:

```bash
cd ~/fabric-workspace/fabric-samples/test-network
./network.sh up createChannel -ca -c mychannel
./network.sh deployCC -c mychannel -ccn certificate-record -ccp "/mnt/c/Users/gagan/OneDrive/Desktop/programs and misc/Mini project/fabric-chaincode/certificate-record" -ccl go
```

Create `fabric-gateway/.env` locally (never commit it) with Org1 MSP certificate, private-key, TLS CA paths, peer endpoint, `mychannel`, `certificate-record`, and the same `GATEWAY_API_TOKEN` as Flask. Then:

```bash
cd /mnt/c/Users/gagan/OneDrive/Desktop/'programs and misc'/'Mini project'/fabric-gateway
npm ci
node --env-file=.env src/server.js
```

The gateway listens only on `127.0.0.1:8081`. Do not expose it, the peer, or Fabric identities publicly. A remote Render application cannot use a WSL-local Fabric network; deploy a protected gateway beside an accessible Fabric network.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite verifies exact-file SHA-256 behavior and the QR-PDF/final-hash issuance transition with a controlled gateway response. Live Fabric tests still require the WSL deployment above.
