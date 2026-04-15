"""FastAPI dependencies: database session and authenticated user resolution."""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.auth_utils import decode_access_token
from app.token_store import validate_access_in_redis
from app.db import get_session
from app.models import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(creds.credentials)
    if claims is None or not validate_access_in_redis(
        claims.user_id, claims.jti, claims.session_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = session.get(User, claims.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_session)]
