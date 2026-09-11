import io

from app.models import Role


def _signup_with_role(client, email, role):
    from tests.conftest import TestingSessionLocal

    signup_response = client.post("/auth/signup", json={"email": email, "password": "hunter2pass"})
    token = signup_response.json()["session_token"]

    if role is not Role.FREE:
        from app.models import User

        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == email).first()
        user.role = role
        db.commit()
        db.close()

    return token


def test_free_user_cannot_upload(client):
    token = _signup_with_role(client, "reader@example.com", Role.FREE)

    response = client.post(
        "/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cover.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")},
    )

    assert response.status_code == 403


def test_admin_can_upload_an_allowed_image_type(client):
    token = _signup_with_role(client, "admin@example.com", Role.ADMIN)

    response = client.post(
        "/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cover.png", io.BytesIO(b"fake image bytes"), "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["url"].startswith("/uploads/")
    assert response.json()["url"].endswith(".png")


def test_upload_rejects_disallowed_file_extension(client):
    token = _signup_with_role(client, "admin2@example.com", Role.ADMIN)

    response = client.post(
        "/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("script.exe", io.BytesIO(b"not an image"), "application/octet-stream")},
    )

    assert response.status_code == 422


def test_upload_rejects_oversized_file(client, monkeypatch):
    token = _signup_with_role(client, "admin3@example.com", Role.ADMIN)
    monkeypatch.setattr("app.storage._MAX_UPLOAD_BYTES", 10)

    response = client.post(
        "/uploads",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cover.jpg", io.BytesIO(b"way more than ten bytes of image data"), "image/jpeg")},
    )

    assert response.status_code == 422


def test_upload_requires_authentication(client):
    response = client.post(
        "/uploads",
        files={"file": ("cover.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")},
    )

    assert response.status_code == 401
