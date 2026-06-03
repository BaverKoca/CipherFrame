# Cipher Frame Deployment Guide

## Multi-Machine Setup (Two-Computer Demo)

This guide provides recommended settings for deploying Cipher Frame across two machines.

### Prerequisites

- Both machines must be on the same network
- Python 3.11+ installed on both
- Virtual environments configured on both

### Machine 1: Backend Server

**Network IP:** Example: `192.168.1.100`

**.env Configuration:**

```env
APP_NAME=Cipher Frame
ENVIRONMENT=production
DEBUG=false
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.100:8000,http://192.168.1.101:8000
DATABASE_PATH=storage/cipher_frame.db
LOG_LEVEL=INFO
SECRET_KEY=<GENERATED_RANDOM_SECRET_32_CHARS_MIN>
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_IMAGE_UPLOAD_BYTES=5242880
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@cipherframe.local
DEFAULT_ADMIN_PASSWORD=<STRONG_PASSWORD_12_CHARS_MIN>
```

**Generate a secure SECRET_KEY:**

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Running the backend:**

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The backend will be accessible at:
- `http://192.168.1.100:8000` (from other machines)
- `http://localhost:8000` (from the same machine)

---

### Machine 2: Frontend Client

**Network IP:** Example: `192.168.1.101`

**Frontend Configuration (in browser):**

Navigate to: `http://192.168.1.100:8000`

All requests will be routed to the backend server on Machine 1.

**Admin Access:**

- Username: `admin`
- Password: `<USE_PASSWORD_FROM_BACKEND_.env>`

---

### Security Considerations

1. **HOST Binding:**
   - `0.0.0.0` binds to all network interfaces (required for multi-machine access)
   - For single-machine testing, use `127.0.0.1` or `localhost`

2. **CORS Origins:**
   - Add all frontend machine IPs to `CORS_ORIGINS`
   - Format: `http://192.168.1.101:8000,http://192.168.1.102:8000`
   - Use commas to separate multiple origins

3. **Required Environment Variables:**
   - `SECRET_KEY` (no default, must be set)
   - `DEFAULT_ADMIN_PASSWORD` (no default, must be set)
   - Application will fail to start if these are missing

4. **JWT Tokens:**
   - Tokens are signed with `SECRET_KEY`
   - All machines must use the same `SECRET_KEY`
   - Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES`

5. **Crypto Test Endpoints:**
   - `/api/crypto/test/des`
   - `/api/crypto/test/rsa`
   - `/api/crypto/test/signature`
   - **Admin access only** (non-admin users receive HTTP 403)
   - Use admin credentials to access

---

### Testing the Setup

**1. Check backend is accessible:**

```powershell
curl -i http://192.168.1.100:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "application": "Cipher Frame"
}
```

**2. Admin login from Machine 2:**

Open browser on Machine 2 (192.168.1.101):

```
http://192.168.1.100:8000/login
```

Enter admin credentials to test authentication across the network.

**3. Verify crypto endpoints require admin:**

Without authentication (should fail with 403):
```powershell
curl -X POST http://192.168.1.100:8000/api/crypto/test/des \
  -H "Content-Type: application/json" \
  -d '{"plaintext":"test"}' \
  -i
```

With admin token:
```powershell
# 1. Get token
$token = (curl -X POST http://192.168.1.100:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<PASSWORD>"}' | ConvertFrom-Json).access_token

# 2. Access crypto endpoint
curl -X POST http://192.168.1.100:8000/api/crypto/test/des \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $token" \
  -d '{"plaintext":"test"}'
```

---

### Troubleshooting

**"Could not validate credentials" on login:**
- Verify `SECRET_KEY` in `.env` hasn't changed since database initialization
- Delete `storage/cipher_frame.db` to reset and re-initialize

**"Admin access required" on crypto endpoints:**
- This is expected for non-admin users
- Use admin credentials to access these endpoints

**CORS errors in browser:**
- Add the frontend machine IP to `CORS_ORIGINS` in backend `.env`
- Restart the backend after changing `CORS_ORIGINS`
- Format: `http://192.168.1.101:8000` (include protocol and port)

**WebSocket connection failures:**
- Verify `BACKEND_HOST=0.0.0.0` (not `127.0.0.1`)
- Ensure firewall allows connections on `BACKEND_PORT`
- WebSocket authentication uses same JWT tokens as REST API

---

### Environment Variable Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `BACKEND_HOST` | No | `0.0.0.0` | `0.0.0.0` for multi-machine, `127.0.0.1` for localhost only |
| `BACKEND_PORT` | No | `8000` | Port number for FastAPI server |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed frontend origins |
| `SECRET_KEY` | **Yes** | None | JWT signing key, must be 32+ random characters |
| `DEFAULT_ADMIN_PASSWORD` | **Yes** | None | Admin account password, must be 12+ characters |
| `DATABASE_PATH` | No | `storage/cipher_frame.db` | Path to SQLite database file |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT token expiration time |

---

### Production Deployment Checklist

- [ ] Generate strong `SECRET_KEY` with `secrets.token_urlsafe(32)`
- [ ] Set strong `DEFAULT_ADMIN_PASSWORD` (12+ chars, mix of types)
- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `CORS_ORIGINS` for production frontend URLs only
- [ ] Set `BACKEND_HOST=0.0.0.0` for accessibility
- [ ] Use HTTPS in production (requires reverse proxy like Nginx)
- [ ] Set up log aggregation and monitoring
- [ ] Test JWT token expiration and renewal
- [ ] Verify WebSocket connections work across network
- [ ] Test crypto endpoint access control

