import io
import zipfile

from app.models import Role, Story, User


def _signup_with_role(client, email, role):
    from tests.conftest import TestingSessionLocal

    signup_response = client.post("/auth/signup", json={"email": email, "password": "hunter2pass"})
    token = signup_response.json()["session_token"]

    if role is not Role.FREE:
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == email).first()
        user.role = role
        db.commit()
        db.close()

    return token


SUBSCRIBERS_CSV = (
    "email,active_subscription,expiry,plan,email_disabled,created_at,first_payment_at\n"
    "free@example.com,false,,other,false,2025-01-01,\n"
    "veteran@example.com,false,,other,false,2025-01-01,2025-06-01\n"
)


def _build_export_zip():
    posts_csv = (
        "post_id,post_date,is_published,email_sent_at,inbox_sent_at,type,audience,title,subtitle,podcast_url\n"
        "111,2026-01-01,true,,,newsletter,everyone,A Real Story,,\n"
    )
    post_html = (
        '<div class="dynamic-content-block" data-dynamic-content="true" data-attrs="{}" '
        'data-dynamic-audiences="non_sub"><div class="dynamic-content-match" '
        'data-dynamic-content-match="true"><p>preview</p></div></div>'
        '<div class="paywall-jump" data-component-name="PaywallToDOM"></div><p>paid</p>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("posts.csv", posts_csv)
        z.writestr("email_list.kumokosmos.csv", SUBSCRIBERS_CSV)
        z.writestr("posts/111.a-real-story.html", post_html)
    buf.seek(0)
    return buf


def test_import_endpoints_require_admin(client):
    reader_token = _signup_with_role(client, "reader@example.com", Role.FREE)

    response = client.post(
        "/admin/import/subscribers",
        files={"file": ("subs.csv", io.BytesIO(SUBSCRIBERS_CSV.encode()), "text/csv")},
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403


def test_import_subscribers_only(client):
    admin_token = _signup_with_role(client, "admin@example.com", Role.ADMIN)

    response = client.post(
        "/admin/import/subscribers",
        files={"file": ("email_list.csv", io.BytesIO(SUBSCRIBERS_CSV.encode()), "text/csv")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created_free"] == 1
    assert body["created_veteran"] == 1


def test_import_subscribers_rejects_non_csv_file(client):
    admin_token = _signup_with_role(client, "admin2@example.com", Role.ADMIN)

    response = client.post(
        "/admin/import/subscribers",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 422


def test_import_full_export(client):
    admin_token = _signup_with_role(client, "admin3@example.com", Role.ADMIN)
    zip_buf = _build_export_zip()

    response = client.post(
        "/admin/import/full",
        files={"file": ("export.zip", zip_buf, "application/zip")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subscribers"]["created_free"] == 1
    assert body["subscribers"]["created_veteran"] == 1
    assert body["posts"]["imported"] == 1


def test_re_running_the_full_import_does_not_duplicate_anything(client):
    admin_token = _signup_with_role(client, "admin4@example.com", Role.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/admin/import/full", files={"file": ("export.zip", _build_export_zip(), "application/zip")}, headers=headers)
    second = client.post(
        "/admin/import/full", files={"file": ("export.zip", _build_export_zip(), "application/zip")}, headers=headers
    )

    body = second.json()
    assert body["subscribers"]["created_free"] == 0  # already existed second time
    assert body["subscribers"]["already_existed"] == 2  
    assert body["posts"]["imported"] == 0
    assert body["posts"]["updated"] == 1  # existing story updated in place, not duplicated


def test_running_subscribers_only_after_full_import_does_not_touch_stories(client):
    from tests.conftest import TestingSessionLocal

    admin_token = _signup_with_role(client, "admin5@example.com", Role.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/admin/import/full", files={"file": ("export.zip", _build_export_zip(), "application/zip")}, headers=headers)

    db = TestingSessionLocal()
    story_count_before = db.query(Story).count()
    db.close()

    client.post(
        "/admin/import/subscribers",
        files={"file": ("email_list.csv", io.BytesIO(SUBSCRIBERS_CSV.encode()), "text/csv")},
        headers=headers,
    )

    db = TestingSessionLocal()
    story_count_after = db.query(Story).count()
    db.close()
    assert story_count_after == story_count_before
