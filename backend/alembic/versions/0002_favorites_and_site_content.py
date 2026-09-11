"""favorites, site content pages

Revision ID: 0002_favorites_and_site_content
Revises: 0001_initial
Create Date: 2026-08-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_favorites_and_site_content"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("story_id", sa.String, sa.ForeignKey("stories.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "story_id", name="uq_favorite_user_story"),
    )

    op.create_table(
        "site_content_pages",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_site_content_pages_slug", "site_content_pages", ["slug"])


def downgrade() -> None:
    op.drop_table("site_content_pages")
    op.drop_table("favorites")
