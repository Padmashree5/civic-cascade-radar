"""
auth.py - Simple JWT authentication for admin routes.
Uses HS256 with a secret from environment variable ADMIN_SECRET.
Default secret is insecure — override via .env in production.
"""
import os
import time
import hmac
import hashlib
import base64
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

_SECRET = os.getenv("ADMIN_SECRET", "dev-secret-change-in-production")
_ADMIN_USER = os.getenv("ADMIN_USER", "admin")
_ADMIN_PASS = os.getenv("ADMIN_PASS", "smartcity2025")
_TOKEN_TTL = 3600 * 8  # 8 hours

security = HTTPBearer(auto_error=False)


# ── Minimal JWT (no external library) ────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_token(username: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": username, "iat": int(time.time()), "exp": int(time.time()) + _TOKEN_TTL}).encode())
    sig = _b64url(hmac.new(_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def _verify_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed")
        header, payload_b64, sig = parts
        expected_sig = _b64url(hmac.new(_SECRET.encode(), f"{header}.{payload_b64}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("bad signature")
        # Pad payload for decoding
        pad = 4 - len(payload_b64) % 4
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * pad))
        if payload["exp"] < time.time():
            raise ValueError("expired")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return _verify_token(credentials.credentials)


# ── Endpoints ────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    if body.username != _ADMIN_USER or body.password != _ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _make_token(body.username)
    return {"access_token": token, "token_type": "bearer", "expires_in": _TOKEN_TTL}


@router.get("/verify")
def verify(user=Depends(require_admin)):
    return {"valid": True, "user": user["sub"], "expires_at": user["exp"]}
