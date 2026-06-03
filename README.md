# Cipher Frame

Cipher Frame is a university-level cybersecurity project for encrypted image messaging. It combines a FastAPI backend, a static browser frontend, SQLite persistence, JWT authentication, role-based administration, WebSocket notifications, and a crypto service layer for image encryption, hashing, signing, and key rotation.

This repository is intended as an educational and demonstrational secure-communication system. It should not be presented as production-grade cryptography without further hardening.

## Features

- User registration and login with bcrypt password hashing
- JWT-based authentication and role-based access control
- Admin dashboard for users, messages, logs, online users, and RSA key metadata
- Encrypted image message sending and receiving
- RSA-based session key exchange for message payloads
- Digital signatures and SHA-256 image integrity verification
- WebSocket notifications for online users and message events
- Environment-based configuration with `.env.example`
- SQLite-backed persistence for local development and demonstrations
- Static frontend served by the FastAPI application

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic Settings
- Database: SQLite
- Authentication: JWT, bcrypt
- Cryptography: PyCryptodome
- Frontend: HTML, CSS, vanilla JavaScript
- Realtime: FastAPI WebSockets

## Project Structure

```text
cipher-frame/
|-- backend/
|   |-- main.py
|   |-- config.py
|   |-- database.py
|   |-- logger.py
|   |-- dependencies/
|   |-- models/
|   |-- routes/
|   |-- schemas/
|   |-- services/
|   |-- tests/
|   |-- websocket/
|   `-- requirements.txt
|-- frontend/
|   |-- admin.html
|   |-- chat.html
|   |-- index.html
|   |-- login.html
|   |-- register.html
|   |-- css/
|   `-- js/
|-- storage/
|   `-- encrypted_images/
|-- docs/
|-- .env.example
|-- .gitignore
|-- DEPLOYMENT_GUIDE.md
|-- HARDENING_SUMMARY.md
`-- README.md
```

## Security Notice

Cipher Frame is built for learning, demonstration, and university project work. The current crypto layer uses DES-CBC for image payload encryption because it matches the project scope, but DES is not recommended for modern production systems. RSA private keys are also stored locally in application persistence and need stronger at-rest protection before any real-world deployment.

For production-oriented work, replace DES-CBC with an authenticated encryption mode such as AES-GCM, protect private keys at rest, add database migrations, add rate limiting, review browser token storage, and run a full security review.

## Prerequisites

- Python 3.11 or newer
- pip
- PowerShell on Windows, or an equivalent terminal on Linux/macOS

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
pip install -r backend/requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` before running the app:

```text
SECRET_KEY=<generate-a-random-secret>
DEFAULT_ADMIN_PASSWORD=<set-a-strong-admin-password>
```

Generate a strong JWT secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running the Application

Start the FastAPI server from the project root:

```powershell
uvicorn backend.main:app --reload
```

Open the application:

```text
http://127.0.0.1:8000/
```

Useful pages:

```text
/login.html
/register.html
/chat.html
/admin.html
```

Health check:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "application": "Cipher Frame"
}
```

## Default Admin

On startup, the application seeds a default admin account if one does not already exist. The username, email, and password come from `.env`:

```text
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@cipherframe.com
DEFAULT_ADMIN_PASSWORD=<your-strong-password>
```

Do not commit your `.env` file or any real database created during local use.

## Tests

The repository currently includes integration-style verification scripts under `backend/tests`. They can be run directly after setting test environment variables.

Example:

```powershell
$env:SECRET_KEY="test-secret-key-for-local-verification-32chars"
$env:DEFAULT_ADMIN_PASSWORD="ChangeMe123!"
$env:DATABASE_PATH="storage/test_cipher_frame.db"
python backend/tests/test_crypto.py
python backend/tests/test_crypto_endpoints_protection.py
python backend/tests/test_websocket_chat.py
python backend/tests/test_image_messages.py
python backend/tests/test_admin_dashboard.py
```

For continuous integration, convert these scripts to isolated `pytest` tests with temporary databases and fixtures.

## Repository Hygiene

The `.gitignore` is configured to keep local secrets and runtime data out of Git:

- `.env` and other local environment files
- SQLite databases
- encrypted image payloads
- generated logs and cache directories
- virtual environments
- local key and certificate files

Before pushing, always check:

```powershell
git status --short
```

Only source code, documentation, `.env.example`, and intentional project assets should be committed.

## Further Documentation

- `DEPLOYMENT_GUIDE.md` explains local network deployment and environment configuration.
- `HARDENING_SUMMARY.md` summarizes security hardening work and remaining production considerations.
- `docs/architecture.md` describes the project architecture.
