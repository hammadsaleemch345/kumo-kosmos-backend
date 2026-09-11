from app.importer.db_import import import_posts, import_subscribers
from app.importer.html_parser import parse_tiers
from app.importer.posts_csv import parse_posts_csv
from app.importer.subscribers_csv import parse_subscribers_csv
from app.models import Story, User


def _dynamic_block(audience: str, inner_html: str) -> str:
    attrs = f'{{&quot;audiences&quot;:[&quot;{audience}&quot;],&quot;displayName&quot;:&quot;x&quot;}}'
    return (
        f'<div class="dynamic-content-block" data-dynamic-content="true" '
        f'data-attrs="{attrs}" data-dynamic-audiences="{audience}">'
        f'<div class="dynamic-content-match" data-dynamic-content-match="true">{inner_html}</div>'
        f"</div>"
    )


def test_parse_tiers_with_explicit_paid_sub_block():
    html = (
        _dynamic_block("non_sub", "<p>preview</p>")
        + _dynamic_block("free_sub", "<p>free part</p><div><hr></div>")  # nested div on purpose
        + _dynamic_block("paid_sub,founding_sub", "<p>the paid part</p>")
    )

    tiers = parse_tiers(html)

    assert tiers.non_sub_html == "<p>preview</p>"
    assert tiers.free_sub_html == "<p>free part</p><div><hr></div>"
    assert tiers.paid_html == "<p>the paid part</p>"
    assert tiers.paid_marker == "dynamic_block"


def test_parse_tiers_with_bare_paywall_jump():
    html = (
        _dynamic_block("non_sub", "<p>preview</p>")
        + _dynamic_block("free_sub", "<p>free part</p>")
        + '<div class="paywall-jump" data-component-name="PaywallToDOM"></div>'
        + "<p>everything after the jump is paid</p>"
    )

    tiers = parse_tiers(html)

    assert tiers.paid_html == "<p>everything after the jump is paid</p>"
    assert tiers.paid_marker == "paywall_jump"


def test_parse_tiers_with_no_paywall_at_all():
    html = "<p>just a poll or announcement, no paywall markers here</p>"

    tiers = parse_tiers(html)

    assert tiers.non_sub_html == ""
    assert tiers.free_sub_html == ""
    assert tiers.paid_html == ""
    assert tiers.paid_marker == "none"


POSTS_CSV = (
    "post_id,post_date,is_published,email_sent_at,inbox_sent_at,type,audience,title,subtitle,podcast_url\n"
    '1,2026-01-01,true,,,newsletter,everyone,A Real Story Title,,\n'
    '2,2026-01-02,true,,,newsletter,everyone,Voting time!,,\n'
    '3,2026-01-03,true,,,page,everyone,About the site,,\n'
    '4,2026-01-04,false,,,newsletter,only_paid,Unpublished Draft Story,,\n'
)


def test_parse_posts_csv_excludes_pages_and_flags_non_story_titles():
    rows = parse_posts_csv(POSTS_CSV)

    ids = {r.post_id: r for r in rows}
    assert "3" not in ids  # type=page, dropped outright
    assert ids["1"].likely_story is True
    assert ids["2"].likely_story is False  # "Voting time!" flagged, not silently dropped
    assert ids["4"].is_published is False


SUBSCRIBERS_CSV = (
    "email,active_subscription,expiry,plan,email_disabled,created_at,first_payment_at\n"
    "free.reader@example.com,false,,other,false,2025-01-01,\n"
    "veteran.by.payment@example.com,false,,other,false,2025-01-01,2025-06-01\n"
    "veteran.by.plan@example.com,true,2026-01-01,monthly,false,2025-01-01,\n"
    "Case.Mixed@Example.com,false,,other,false,2025-01-01,\n"
)


def test_parse_subscribers_csv_classifies_veteran_status():
    rows = parse_subscribers_csv(SUBSCRIBERS_CSV)
    by_email = {r.email: r for r in rows}

    assert by_email["free.reader@example.com"].is_veteran is False
    assert by_email["veteran.by.payment@example.com"].is_veteran is True
    assert by_email["veteran.by.plan@example.com"].is_veteran is True


def test_parse_subscribers_csv_lowercases_email():
    rows = parse_subscribers_csv(SUBSCRIBERS_CSV)

    assert any(r.email == "case.mixed@example.com" for r in rows)


def test_import_subscribers_is_idempotent_and_only_imports_email_for_veterans(client):
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    rows = parse_subscribers_csv(SUBSCRIBERS_CSV)

    first_summary = import_subscribers(db, rows)
    assert first_summary.created_free == 2  # free.reader + case.mixed
    assert first_summary.created_veteran == 2

    veteran = db.query(User).filter(User.email == "veteran.by.payment@example.com").first()
    assert veteran.is_veteran_sub is True
    assert veteran.password_hash is None  # no plan/payment data imported, no password either

    # Re-running with the exact same export must not create duplicates.
    second_summary = import_subscribers(db, rows)
    assert second_summary.created_free == 0
    assert second_summary.created_veteran == 0
    assert second_summary.already_existed == 4

    total_users = db.query(User).count()
    assert total_users == 4
    db.close()


def test_import_posts_is_idempotent_by_substack_post_id(client):
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    rows = parse_posts_csv(POSTS_CSV)
    html = _dynamic_block("non_sub", "<p>preview</p>") + _dynamic_block("free_sub", "<p>free</p>")
    html_by_id = {"1": html}
    slug_by_id = {"1": "a-real-story-title"}

    first_summary = import_posts(db, rows, html_by_id, slug_by_id)
    assert first_summary.imported == 1  # only post 1: page excluded, poll flagged, draft unpublished
    assert first_summary.skipped_non_story == 1
    assert first_summary.skipped_unpublished == 1

    story = db.query(Story).filter(Story.substack_post_id == "1").first()
    assert story.slug == "a-real-story-title"
    assert story.free_wall_marker == len("<p>preview</p>")

    # Re-running updates the existing story instead of creating a second one.
    second_summary = import_posts(db, rows, html_by_id, slug_by_id)
    assert second_summary.imported == 0
    assert second_summary.updated == 1
    assert db.query(Story).count() == 1
    db.close()
