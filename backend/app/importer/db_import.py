from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession

from app.importer.html_parser import parse_tiers
from app.importer.posts_csv import PostRow
from app.importer.subscribers_csv import SubscriberRow
from app.models import Story, User


@dataclass
class SubscriberImportSummary:
    created_free: int = 0
    created_veteran: int = 0
    already_existed: int = 0


def import_subscribers(db: DBSession, rows: list[SubscriberRow]) -> SubscriberImportSummary:
    """Idempotent by email: re-running with the same export never creates duplicate users and
    never clears veteran_outreach_sent_at, so a re-run can't cause a veteran to be emailed twice
    once the outreach-sending step (YNOT Mail) marks that timestamp.
    """
    summary = SubscriberImportSummary()

    for row in rows:
        existing = db.query(User).filter(User.email == row.email).first()
        if existing is not None:
            if row.is_veteran and not existing.is_veteran_sub:
                existing.is_veteran_sub = True
            summary.already_existed += 1
            continue

        db.add(User(email=row.email, password_hash=None, is_veteran_sub=row.is_veteran))
        if row.is_veteran:
            summary.created_veteran += 1
        else:
            summary.created_free += 1

    db.commit()
    return summary


@dataclass
class PostImportSummary:
    imported: int = 0
    updated: int = 0
    skipped_non_story: int = 0
    skipped_unpublished: int = 0


def import_posts(
    db: DBSession,
    post_rows: list[PostRow],
    html_by_post_id: dict[str, str],
    slug_by_post_id: dict[str, str],
) -> PostImportSummary:
    """Idempotent by substack_post_id: re-running updates the existing story's content/markers
    instead of creating a duplicate, since the client will keep posting on Substack mid-build
    and re-run this periodically.
    """
    summary = PostImportSummary()

    for row in post_rows:
        if not row.is_published:
            summary.skipped_unpublished += 1
            continue
        if not row.likely_story:
            summary.skipped_non_story += 1
            continue

        html = html_by_post_id.get(row.post_id, "")
        tiers = parse_tiers(html)
        content = tiers.non_sub_html + tiers.free_sub_html + tiers.paid_html
        free_wall_marker = len(tiers.non_sub_html)
        paid_wall_marker = len(tiers.non_sub_html) + len(tiers.free_sub_html)

        existing = db.query(Story).filter(Story.substack_post_id == row.post_id).first()
        if existing is not None:
            existing.title = row.title
            existing.content = content
            existing.free_wall_marker = free_wall_marker
            existing.paid_wall_marker = paid_wall_marker
            summary.updated += 1
            continue

        db.add(
            Story(
                title=row.title,
                slug=slug_by_post_id.get(row.post_id, row.post_id),
                content=content,
                free_wall_marker=free_wall_marker,
                paid_wall_marker=paid_wall_marker,
                is_published=True,
                substack_post_id=row.post_id,
            )
        )
        summary.imported += 1

    db.commit()
    return summary
