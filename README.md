# Government Document Management and Verification System

Flask and PostgreSQL application for citizens, administrators, document applications, and later Hyperledger Fabric certificate verification.

## Setup

1. Install Python 3.14 and PostgreSQL 18.6 (or compatible supported versions).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` and `SECRET_KEY`.
3. Create database `gov_document_management` in PostgreSQL.
4. Create and activate a virtual environment, then run `pip install -r requirements.txt`.
5. Run `python run.py` and open `http://127.0.0.1:5000`.

Development OTPs are printed only to the Flask terminal. Create the first administrator with `flask --app run create-admin`.
