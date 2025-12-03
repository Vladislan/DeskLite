from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from passlib.context import CryptContext
from jose import jwt, JWTError

ALGORITHM = "HS256"
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_ctx.verify(plain_password, password_hash)

def create_access_token(*, subject: str, role: str, secret: str, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def decode_token(token: str, secret: str) -> Dict[str, Any]:
    try:
        data = jwt.decode(token, secret, algorithms=[ALGORITHM])
        if data.get("type") != "access" or "sub" not in data:
            raise ValueError("invalid_token_payload")
        return data
    except JWTError as e:
        raise ValueError("invalid_token") from e

# backward-compat
def decode_access_token(token: str, secret: str):
    return decode_token(token, secret)
