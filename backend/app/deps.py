from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Role, Session, User
from app.security import hash_token, utcnow


def get_current_session(
    authorization: str = Header(default=""),
    db: DBSession = Depends(get_db),
) -> Session:
    """Resolve the bearer token to an active, unrevoked, unexpired session record."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    raw_token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)
    session = db.query(Session).filter(Session.token_hash == token_hash).first()

    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at < utcnow()
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid")

    return session


def get_current_user(
    session: Session = Depends(get_current_session),
    db: DBSession = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is inactive")
    return user


def get_current_user_optional(
    authorization: str = Header(default=""),
    db: DBSession = Depends(get_db),
) -> User | None:
    """Like get_current_user, but returns None instead of 401 when there's no/invalid token.

    For endpoints guests are allowed to hit (reading a story preview) where the response still
    needs to vary by who's asking. A malformed or expired token here is null, not misauthenticated:
    treat the caller as a guest rather than error out, since the whole point is guests are welcome.
    """
    if not authorization.startswith("Bearer "):
        return None

    raw_token = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw_token)
    session = db.query(Session).filter(Session.token_hash == token_hash).first()

    if session is None or session.revoked_at is not None or session.expires_at < utcnow():
        return None

    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
    return user


def require_role(*allowed_roles: Role):
    """Dependency factory: 403s any user whose role isn't in allowed_roles. Staff-only endpoints
    (admin dashboard, uploads, discount codes) should depend on this rather than get_current_user
    alone, so a logged-in reader can't reach them just by having a valid session.
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this action")
        return user

    return _check
