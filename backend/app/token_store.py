"""Redis-backed refresh rotation, access-token allowlist, and session invalidation."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import redis
from starlette.responses import Response

from app.auth_utils import encode_access_token
from app.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _refresh_ttl_seconds() -> int:
    return settings.jwt_refresh_expire_days * 86400


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def session_version_key(user_id: int) -> str:
    return f"user:{user_id}:sv"


def get_session_version(user_id: int) -> int:
    r = get_redis()
    v = r.get(session_version_key(user_id))
    return int(v) if v is not None else 0


def bump_session_version(user_id: int) -> int:
    return int(get_redis().incr(session_version_key(user_id)))


def register_access_token(user_id: int, jti: str, ttl_seconds: int) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.set(f"access:{jti}", str(user_id), ex=ttl_seconds)
    pipe.sadd(f"user:{user_id}:jtis", jti)
    pipe.execute()


def validate_access_in_redis(user_id: int, jti: str, claimed_sv: int) -> bool:
    r = get_redis()
    if int(r.get(session_version_key(user_id)) or 0) != claimed_sv:
        return False
    stored = r.get(f"access:{jti}")
    return stored is not None and int(stored) == user_id


def revoke_access_jti(jti: str) -> None:
    r = get_redis()
    uid = r.get(f"access:{jti}")
    r.delete(f"access:{jti}")
    if uid is not None:
        r.srem(f"user:{int(uid)}:jtis", jti)


def _delete_family_refresh_tokens(family_id: str, user_id: int) -> None:
    r = get_redis()
    hashes = r.smembers(f"family:{family_id}:hashes")
    for h in hashes:
        r.delete(f"refresh:{h}")
    r.delete(f"family:{family_id}")
    r.delete(f"family:{family_id}:hashes")
    r.srem(f"user:{user_id}:families", family_id)


def _nuke_family_reuse(family_id: str, user_id: int) -> None:
    _delete_family_refresh_tokens(family_id, user_id)
    bump_session_version(user_id)


@dataclass
class RefreshRecord:
    user_id: int
    family_id: str
    stale: bool


def _parse_refresh_payload(raw: str) -> RefreshRecord | None:
    try:
        obj: dict[str, Any] = json.loads(raw)
        return RefreshRecord(
            user_id=int(obj["user_id"]),
            family_id=str(obj["family_id"]),
            stale=bool(obj.get("stale")),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def issue_refresh_token(user_id: int) -> str:
    """Create a new refresh family and return the raw cookie value."""
    r = get_redis()
    family_id = str(uuid.uuid4())
    raw = secrets.token_urlsafe(32)
    h = _hash_refresh(raw)
    ttl = _refresh_ttl_seconds()
    payload = json.dumps({"user_id": user_id, "family_id": family_id, "stale": False})
    pipe = r.pipeline()
    pipe.set(f"refresh:{h}", payload, ex=ttl)
    pipe.set(f"family:{family_id}", h, ex=ttl)
    pipe.sadd(f"family:{family_id}:hashes", h)
    pipe.sadd(f"user:{user_id}:families", family_id)
    pipe.execute()
    return raw


def rotate_refresh_token(raw_cookie: str) -> tuple[int, str] | None:
    """
    Validate refresh cookie, enforce rotation + reuse detection.
    Returns (user_id, new_raw_refresh), or None if invalid / reuse.
    """
    if not raw_cookie:
        return None
    r = get_redis()
    h = _hash_refresh(raw_cookie)
    row = r.get(f"refresh:{h}")
    if row is None:
        return None
    rec = _parse_refresh_payload(row)
    if rec is None:
        return None
    if rec.stale:
        _nuke_family_reuse(rec.family_id, rec.user_id)
        return None
    active = r.get(f"family:{rec.family_id}")
    if active != h:
        _nuke_family_reuse(rec.family_id, rec.user_id)
        return None

    new_raw = secrets.token_urlsafe(32)
    new_h = _hash_refresh(new_raw)
    ttl = _refresh_ttl_seconds()
    new_payload = json.dumps(
        {"user_id": rec.user_id, "family_id": rec.family_id, "stale": False}
    )
    stale_payload = json.dumps(
        {"user_id": rec.user_id, "family_id": rec.family_id, "stale": True}
    )
    pipe = r.pipeline()
    pipe.set(f"refresh:{h}", stale_payload, ex=ttl)
    pipe.set(f"refresh:{new_h}", new_payload, ex=ttl)
    pipe.set(f"family:{rec.family_id}", new_h, ex=ttl)
    pipe.sadd(f"family:{rec.family_id}:hashes", new_h)
    pipe.execute()
    return rec.user_id, new_raw


def revoke_refresh_cookie(raw_cookie: str | None) -> None:
    if not raw_cookie:
        return
    r = get_redis()
    h = _hash_refresh(raw_cookie)
    row = r.get(f"refresh:{h}")
    if row is None:
        return
    rec = _parse_refresh_payload(row)
    if rec is None:
        return
    _delete_family_refresh_tokens(rec.family_id, rec.user_id)


def purge_all_sessions_for_user(user_id: int) -> None:
    """Invalidate every refresh + access token and bump session version."""
    r = get_redis()
    families = list(r.smembers(f"user:{user_id}:families"))
    for fid in families:
        _delete_family_refresh_tokens(fid, user_id)
    r.delete(f"user:{user_id}:families")
    jtis = list(r.smembers(f"user:{user_id}:jtis"))
    for jti in jtis:
        r.delete(f"access:{jti}")
    r.delete(f"user:{user_id}:jtis")
    bump_session_version(user_id)


def mint_access_token(user_id: int) -> str:
    """Issue a short-lived JWT registered in Redis."""
    jti = str(uuid.uuid4())
    sv = get_session_version(user_id)
    ttl_min = settings.jwt_access_expire_minutes
    ttl_sec = ttl_min * 60
    token = encode_access_token(user_id=user_id, jti=jti, session_version=sv, ttl_minutes=ttl_min)
    register_access_token(user_id, jti, ttl_sec)
    return token


def attach_refresh_cookie(response: Response, raw_refresh: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_refresh,
        max_age=settings.jwt_refresh_expire_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
