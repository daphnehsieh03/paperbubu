from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.auth_utils import decode_access_token, hash_password, verify_password
from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.models import LoginRequest, RegisterRequest, TokenResponse, User
from app.token_store import (
    attach_refresh_cookie,
    clear_refresh_cookie,
    issue_refresh_token,
    mint_access_token,
    purge_all_sessions_for_user,
    revoke_access_jti,
    revoke_refresh_cookie,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_optional = HTTPBearer(auto_error=False)


def _user_for_login(session: Session, identifier: str) -> User | None:
    if "@" in identifier:
        key = identifier.lower()
        return session.exec(select(User).where(func.lower(User.email) == key)).first()
    return session.exec(select(User).where(User.username == identifier.lower())).first()


def _issue_session(response: Response, user_id: int) -> TokenResponse:
    refresh = issue_refresh_token(user_id)
    attach_refresh_cookie(response, refresh)
    access = mint_access_token(user_id)
    return TokenResponse(access_token=access)


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, session: SessionDep, response: Response) -> TokenResponse:
    existing_email = session.exec(select(User).where(User.email == body.email)).first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    existing_username = session.exec(select(User).where(User.username == body.username)).first()
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    user = User(
        email=body.email,
        username=body.username,
        password_hash=hash_password(body.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        # catching the UNIQUE constraint violation error. instead of raising 500, we return a 409
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )
    session.refresh(user)
    return _issue_session(response, user.id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: SessionDep, response: Response) -> TokenResponse:
    user = _user_for_login(session, body.identifier)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, username, or password",
        )
    return _issue_session(response, user.id)


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(request: Request, response: Response) -> TokenResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    rotated = rotate_refresh_token(raw or "")
    if rotated is None:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh session",
        )
    user_id, new_raw = rotated
    attach_refresh_cookie(response, new_raw)
    access = mint_access_token(user_id)
    return TokenResponse(access_token=access)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_optional)],
) -> dict[str, bool]:
    raw = request.cookies.get(settings.refresh_cookie_name)
    revoke_refresh_cookie(raw)
    if creds and creds.credentials:
        claims = decode_access_token(creds.credentials)
        if claims:
            revoke_access_jti(claims.jti)
    clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/logout-all")
def logout_all(
    response: Response,
    user: CurrentUser,
) -> dict[str, bool]:
    purge_all_sessions_for_user(user.id)
    clear_refresh_cookie(response)
    return {"ok": True}
