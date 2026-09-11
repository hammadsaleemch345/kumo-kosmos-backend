import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.security import utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    FREE = "free"
    PAID = "paid"
    ADMIN = "admin"
    OWNER = "owner"


class SubscriptionStatus(str, enum.Enum):
    NONE = "none"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    CHARGEBACK = "chargeback"


class Tier(Base):
    """A subscription tier. Free and Paid are core/locked; anything else is admin-created."""

    __tablename__ = "tiers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    billing_period: Mapped[str] = mapped_column(String, nullable=False, default="monthly")
    is_core: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    perks: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    # Nullable because imported subscribers (Substack) have no password until they claim their
    # account via the password reset flow. A signup/login can never succeed while this is None.
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    # values_callable is required: SQLAlchemy's Enum column defaults to inserting the Python
    # enum member's NAME ("FREE"), but the Postgres enum type (see the migration) was created
    # with lowercase VALUES ("free"). Without this, every insert 500s against real Postgres —
    # SQLite let it slide silently since it has no native enum type to enforce the mismatch.
    role: Mapped[Role] = mapped_column(
        Enum(Role, values_callable=lambda e: [m.value for m in e]), nullable=False, default=Role.FREE
    )
    tier_id: Mapped[str | None] = mapped_column(ForeignKey("tiers.id"), nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=SubscriptionStatus.NONE,
    )
    ccbill_subscription_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    is_veteran_sub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    veteran_discount_redeemed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    veteran_outreach_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    tier: Mapped[Tier | None] = relationship()
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """A server-side session record so logout can actually revoke access, not just delete a client token."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    free_wall_marker: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_wall_marker: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set only for Substack-imported stories, unique so re-running the importer updates the
    # existing row instead of creating a duplicate story.
    substack_post_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    question: Mapped[str] = mapped_column(String, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_bookmark_user_story"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False)
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "story_id", name="uq_favorite_user_story"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SiteContentPage(Base):
    """Admin-editable static pages (About, FAQ, Terms, Contact). `slug` is the lookup key the
    public site fetches by, kept as a small fixed set rather than a general CMS.
    """

    __tablename__ = "site_content_pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    percent_off: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PaymentEvent(Base):
    """Raw log of every CCBill webhook received, kept separate from User.subscription_status on
    purpose per the SOW's architecture note: payment event handling stays isolated from
    subscription logic, so a bad webhook retry or an unrecognized event type can't corrupt
    subscriber state, and every raw event is auditable independent of how it was interpreted.
    """

    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("ccbill_subscription_id", "event_type", "ccbill_timestamp", name="uq_payment_event"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    ccbill_subscription_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    ccbill_timestamp: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
