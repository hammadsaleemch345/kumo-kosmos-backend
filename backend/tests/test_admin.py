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


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _story_payload(slug="a-story", **overrides):
    payload = {"title": "A Story", "slug": slug, "content": "<p>hi</p>"}
    payload.update(overrides)
    return payload


def test_free_user_cannot_list_stories(client):
    token = _signup_with_role(client, "reader@example.com", Role.FREE)

    response = client.get("/admin/stories", headers=_auth(token))

    assert response.status_code == 403


def test_admin_can_create_list_update_and_delete_a_story(client):
    token = _signup_with_role(client, "admin@example.com", Role.ADMIN)

    create_response = client.post("/admin/stories", json=_story_payload(), headers=_auth(token))
    assert create_response.status_code == 201
    story_id = create_response.json()["id"]

    list_response = client.get("/admin/stories", headers=_auth(token))
    assert len(list_response.json()) == 1

    update_response = client.patch(
        f"/admin/stories/{story_id}", json={"is_published": True}, headers=_auth(token)
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_published"] is True
    assert update_response.json()["title"] == "A Story"  # untouched fields survive a partial update

    delete_response = client.delete(f"/admin/stories/{story_id}", headers=_auth(token))
    assert delete_response.status_code == 204
    assert client.get("/admin/stories", headers=_auth(token)).json() == []


def test_creating_a_story_with_a_duplicate_slug_is_rejected(client):
    token = _signup_with_role(client, "admin2@example.com", Role.ADMIN)
    client.post("/admin/stories", json=_story_payload(slug="dupe"), headers=_auth(token))

    response = client.post("/admin/stories", json=_story_payload(slug="dupe"), headers=_auth(token))

    assert response.status_code == 409


def test_updating_a_nonexistent_story_returns_404(client):
    token = _signup_with_role(client, "admin3@example.com", Role.ADMIN)

    response = client.patch("/admin/stories/does-not-exist", json={"is_published": True}, headers=_auth(token))

    assert response.status_code == 404


def test_owner_can_also_manage_stories(client):
    token = _signup_with_role(client, "owner@example.com", Role.OWNER)

    response = client.post("/admin/stories", json=_story_payload(), headers=_auth(token))

    assert response.status_code == 201


def test_free_user_cannot_list_subscribers(client):
    token = _signup_with_role(client, "reader2@example.com", Role.FREE)

    response = client.get("/admin/subscribers", headers=_auth(token))

    assert response.status_code == 403


def test_admin_can_list_and_search_subscribers(client):
    admin_token = _signup_with_role(client, "admin4@example.com", Role.ADMIN)
    _signup_with_role(client, "veteran-reader@example.com", Role.FREE)

    all_subs = client.get("/admin/subscribers", headers=_auth(admin_token))
    assert len(all_subs.json()) == 2  # the admin itself plus the new reader

    search_response = client.get(
        "/admin/subscribers", params={"search": "veteran-reader"}, headers=_auth(admin_token)
    )
    assert len(search_response.json()) == 1
    assert search_response.json()[0]["email"] == "veteran-reader@example.com"


def test_admin_can_filter_subscribers_to_veterans_only(client):
    from tests.conftest import TestingSessionLocal

    admin_token = _signup_with_role(client, "admin5@example.com", Role.ADMIN)
    _signup_with_role(client, "regular@example.com", Role.FREE)

    db = TestingSessionLocal()
    db.add(User(email="imported-veteran@example.com", password_hash=None, is_veteran_sub=True))
    db.commit()
    db.close()

    response = client.get("/admin/subscribers", params={"veteran_only": True}, headers=_auth(admin_token))

    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "imported-veteran@example.com"
