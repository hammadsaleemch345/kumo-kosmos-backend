import zipfile

from app.importer.zip_import import run_substack_import
from app.models import Story, User


def _build_export_zip(path):
    posts_csv = (
        "post_id,post_date,is_published,email_sent_at,inbox_sent_at,type,audience,title,subtitle,podcast_url\n"
        "111,2026-01-01,true,,,newsletter,everyone,A Real Story,,\n"
        "222,2026-01-02,true,,,page,everyone,About,,\n"
    )
    email_list_csv = (
        "email,active_subscription,expiry,plan,email_disabled,created_at,first_payment_at\n"
        "free@example.com,false,,other,false,2025-01-01,\n"
        "veteran@example.com,false,,other,false,2025-01-01,2025-06-01\n"
    )
    post_html = (
        '<div class="dynamic-content-block" data-dynamic-content="true" '
        'data-attrs="{}" data-dynamic-audiences="non_sub">'
        '<div class="dynamic-content-match" data-dynamic-content-match="true"><p>preview</p></div></div>'
        '<div class="dynamic-content-block" data-dynamic-content="true" '
        'data-attrs="{}" data-dynamic-audiences="free_sub">'
        '<div class="dynamic-content-match" data-dynamic-content-match="true"><p>free</p></div></div>'
        '<div class="paywall-jump" data-component-name="PaywallToDOM"></div><p>paid</p>'
    )

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("posts.csv", posts_csv)
        z.writestr("email_list.kumokosmos.csv", email_list_csv)
        z.writestr("posts/111.a-real-story.html", post_html)
        z.writestr("posts/111.delivers.csv", "post_id,timestamp,email\n")


def test_run_substack_import_end_to_end_from_a_real_zip(client, tmp_path):
    from tests.conftest import TestingSessionLocal

    zip_path = tmp_path / "export.zip"
    _build_export_zip(zip_path)

    db = TestingSessionLocal()
    result = run_substack_import(db, str(zip_path))

    assert result.subscribers.created_free == 1
    assert result.subscribers.created_veteran == 1
    assert result.posts.imported == 1  # the page row is excluded automatically

    story = db.query(Story).filter(Story.substack_post_id == "111").first()
    assert story.slug == "a-real-story"
    assert "preview" in story.content
    assert "paid" in story.content

    veteran = db.query(User).filter(User.email == "veteran@example.com").first()
    assert veteran.is_veteran_sub is True
    db.close()
