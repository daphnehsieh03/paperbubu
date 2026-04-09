from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth_utils import create_access_token, hash_password, verify_password
from app.deps import SessionDep
from app.models import User
from app.models import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, session: SessionDep) -> TokenResponse:
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    user = session.exec(select(User).where(User.email == body.email)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
