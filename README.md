# Government Document Management and Verification System

Flask and PostgreSQL application for citizens, administrators, document applications, and later Hyperledger Fabric certificate verification.

## Setup

1. Install Python 3.14 and PostgreSQL (18.6 or a compatible supported version).
2. Copy `.env.example` to `.env` and set `DATABASE_URL` and `SECRET_KEY`.
3. Create database `gov_document_management` in PostgreSQL.
4. Create and activate a virtual environment, then run `pip install -r requirements.txt`.
5. Activate the virtual environment and run `python run.py`, then open `http://127.0.0.1:5000`.

On Windows PowerShell, activate the environment with `\.venv\Scripts\Activate.ps1`. You can also start the app directly with `\.venv\Scripts\python.exe run.py`.

`FLASK_DEBUG` defaults to `false`, and the built-in server's automatic reloader is disabled to avoid restarting Python during startup. Set `FLASK_DEBUG=true` in `.env` only when you need the interactive debugger. The “development server” warning is expected for local use; use a production WSGI server when deploying publicly. A `KeyboardInterrupt` traceback means the process was interrupted (usually with Ctrl+C); it is not the Flask development-server warning.

Development OTPs are printed only to the Flask terminal. Create the first administrator with `flask --app run create-admin`.
