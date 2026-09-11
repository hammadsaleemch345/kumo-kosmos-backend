from app.models import Role, User


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


def test_reading_a_page_that_does_not_exist_yet_404s(client):
    response = client.get("/pages/about")

    assert response.status_code == 404


def test_admin_can_create_and_the_public_can_read_a_page(client):
    admin_token = _signup_with_role(client, "admin@example.com", Role.ADMIN)

    create_response = client.put(
        "/admin/pages/about",
        json={"title": "About the Author", "content": "Some real content here."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 200

    public_response = client.get("/pages/about")
    assert public_response.status_code == 200
    assert public_response.json() == {
        "slug": "about",
        "title": "About the Author",
        "content": "Some real content here.",
    }


def test_updating_a_page_overwrites_in_place_not_duplicates(client):
    admin_token = _signup_with_role(client, "admin2@example.com", Role.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    client.put("/admin/pages/faq", json={"title": "FAQ", "content": "v1"}, headers=headers)
    client.put("/admin/pages/faq", json={"title": "FAQ", "content": "v2"}, headers=headers)

    response = client.get("/pages/faq")
    assert response.json()["content"] == "v2"


def test_free_user_cannot_edit_pages(client):
    reader_token = _signup_with_role(client, "reader@example.com", Role.FREE)

    response = client.put(
        "/admin/pages/tos",
        json={"title": "Terms", "content": "..."},
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403


def test_editing_pages_requires_authentication(client):
    response = client.put("/admin/pages/tos", json={"title": "Terms", "content": "..."})

    assert response.status_code == 401
