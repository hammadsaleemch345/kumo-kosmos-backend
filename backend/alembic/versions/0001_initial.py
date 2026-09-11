"""initial schema: users, sessions, password reset tokens, tiers, stories, polls, bookmarks, discount codes

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_ENUM = sa.Enum("free", "paid", "admin", "owner", name="role")
SUBSCRIPTION_STATUS_ENUM = sa.Enum("none", "active", "past_due", "cancelled", "chargeback", name="subscriptionstatus")


def upgrade() -> None:
    op.create_table(
        "tiers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("price_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("billing_period", sa.String, nullable=False, server_default="monthly"),
        sa.Column("is_core", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("perks", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("password_hash", sa.String, nullable=True),
        sa.Column("role", ROLE_ENUM, nullable=False, server_default="free"),
        sa.Column("tier_id", sa.String, sa.ForeignKey("tiers.id"), nullable=True),
        sa.Column("subscription_status", SUBSCRIPTION_STATUS_ENUM, nullable=False, server_default="none"),
        sa.Column("ccbill_subscription_id", sa.String, nullable=True, unique=True),
        sa.Column("is_veteran_sub", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("veteran_discount_redeemed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("veteran_outreach_sent_at", sa.DateTime, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    op.create_table(
        "stories",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("cover_url", sa.String, nullable=True),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("free_wall_marker", sa.Integer, nullable=True),
        sa.Column("paid_wall_marker", sa.Integer, nullable=True),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("substack_post_id", sa.String, nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stories_slug", "stories", ["slug"])

    op.create_table(
        "polls",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("question", sa.String, nullable=False),
        sa.Column("is_closed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("closes_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("story_id", sa.String, sa.ForeignKey("stories.id"), nullable=False),
        sa.Column("passage_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "story_id", name="uq_bookmark_user_story"),
    )

    op.create_table(
        "discount_codes",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("code", sa.String, nullable=False, unique=True),
        sa.Column("percent_off", sa.Integer, nullable=False),
        sa.Column("duration_months", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_discount_codes_code", "discount_codes", ["code"])

    op.create_table(
        "payment_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("ccbill_subscription_id", sa.String, nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("ccbill_timestamp", sa.String, nullable=False),
        sa.Column("raw_payload", sa.Text, nullable=False),
        sa.Column("received_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "ccbill_subscription_id", "event_type", "ccbill_timestamp", name="uq_payment_event"
        ),
    )
    op.create_index("ix_payment_events_ccbill_subscription_id", "payment_events", ["ccbill_subscription_id"])


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("discount_codes")
    op.drop_table("bookmarks")
    op.drop_table("polls")
    op.drop_table("stories")
    op.drop_table("password_reset_tokens")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("tiers")
    ROLE_ENUM.drop(op.get_bind(), checkfirst=True)
    SUBSCRIPTION_STATUS_ENUM.drop(op.get_bind(), checkfirst=True)
