from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_session, get_current_user
from app.models import PasswordResetToken, Session, User
from app.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignupRequest,
    UserResponse,
)
from app.security import expires_in, generate_token, hash_password, hash_token, utcnow, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_session(user: User, db: DBSession) -> str:
    raw_token, token_hash = generate_token()
    db.add(
        Session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_in(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    return raw_token


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: DBSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_session(user, db)
    return AuthResponse(session_token=token, email=user.email, role=user.role.value)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)) -> AuthResponse:
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    # user.password_hash is None for imported subscribers who haven't claimed their account yet
    # (via password reset), so this must short-circuit before calling verify_password on None.
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = _create_session(user, db)
    return AuthResponse(session_token=token, email=user.email, role=user.role.value)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(email=user.email, role=user.role.value)


@router.post("/logout", response_model=MessageResponse)
def logout(
    session: Session = Depends(get_current_session),
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    session.revoked_at = utcnow()
    db.commit()
    return MessageResponse(message="Logged out")


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(payload: PasswordResetRequest, db: DBSession = Depends(get_db)) -> MessageResponse:
    """Always returns the same message regardless of whether the email exists, to avoid leaking which emails are registered."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is not None:
        raw_token, token_hash = generate_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_in(minutes=settings.password_reset_ttl_minutes),
            )
        )
        db.commit()
        # TODO(YNOT Mail integration): send raw_token via the password reset email template.

    return MessageResponse(message="If that email is registered, a reset link has been sent")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(payload: PasswordResetConfirm, db: DBSession = Depends(get_db)) -> MessageResponse:
    token_hash = hash_token(payload.token)
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at < utcnow()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset token is invalid or expired")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    user.password_hash = hash_password(payload.new_password)
    reset_token.used_at = utcnow()
    db.commit()
    return MessageResponse(message="Password updated, you can now log in")
