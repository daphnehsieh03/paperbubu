"""Password hashing and JWT encode/decode (no FastAPI Depends)."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AccessClaims(BaseModel):
    user_id: int
    jti: str
    session_version: int


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def encode_access_token(
    *,
    user_id: int,
    jti: str,
    session_version: int,
    ttl_minutes: int,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "sv": session_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessClaims | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        jti = payload.get("jti")
        sv = payload.get("sv")
        if sub is None or jti is None or sv is None:
            return None
        return AccessClaims(user_id=int(sub), jti=str(jti), session_version=int(sv))
    except JWTError:
        return None
