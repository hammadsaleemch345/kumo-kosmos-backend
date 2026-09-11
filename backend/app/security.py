import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token goes to the client, only the hash is stored."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def utcnow() -> datetime:
    """Naive UTC timestamp, matching the naive DateTime columns used throughout the schema."""
    return datetime.now(UTC).replace(tzinfo=None)


def expires_in(hours: int = 0, minutes: int = 0) -> datetime:
    return utcnow() + timedelta(hours=hours, minutes=minutes)
