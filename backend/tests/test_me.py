from app.models import Role, Story, User


def _signup(client, email="reader@example.com"):
    response = client.post("/auth/signup", json={"email": email, "password": "hunter2pass"})
    return response.json()["session_token"]


def _make_admin(client):
    return _signup_with_role(client, "admin@example.com", Role.ADMIN)


def _signup_with_role(client, email, role):
    from tests.conftest import TestingSessionLocal

    token = _signup(client, email)
    if role is not Role.FREE:
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == email).first()
        user.role = role
        db.commit()
        db.close()
    return token


def _create_story(client, admin_token, slug="a-story"):
    response = client.post(
        "/admin/stories",
        json={"title": "A Story", "slug": slug, "content": "<p>hi</p>", "is_published": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return response.json()["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_bookmark_requires_login(client):
    response = client.put("/me/bookmarks", json={"story_id": "whatever"})

    assert response.status_code == 401


def test_bookmark_upsert_is_idempotent_per_story(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_token = _signup(client, "reader1@example.com")

    first = client.put(
        "/me/bookmarks",
        json={"story_id": story_id, "passage_text": "the first passage"},
        headers=_auth(reader_token),
    )
    assert first.status_code == 200
    assert first.json()["passage_text"] == "the first passage"

    second = client.put(
        "/me/bookmarks",
        json={"story_id": story_id, "passage_text": "an updated passage"},
        headers=_auth(reader_token),
    )
    assert second.status_code == 200
    assert second.json()["passage_text"] == "an updated passage"

    listing = client.get("/me/bookmarks", headers=_auth(reader_token))
    assert len(listing.json()) == 1  # updated in place, not duplicated


def test_bookmark_persists_across_requests(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_token = _signup(client, "reader2@example.com")

    client.put("/me/bookmarks", json={"story_id": story_id}, headers=_auth(reader_token))

    listing = client.get("/me/bookmarks", headers=_auth(reader_token))
    assert listing.status_code == 200
    assert listing.json()[0]["story_id"] == story_id


def test_bookmark_for_nonexistent_story_404s(client):
    reader_token = _signup(client, "reader3@example.com")

    response = client.put("/me/bookmarks", json={"story_id": "does-not-exist"}, headers=_auth(reader_token))

    assert response.status_code == 404


def test_delete_bookmark(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_token = _signup(client, "reader4@example.com")
    client.put("/me/bookmarks", json={"story_id": story_id}, headers=_auth(reader_token))

    delete_response = client.delete(f"/me/bookmarks/{story_id}", headers=_auth(reader_token))
    assert delete_response.status_code == 204

    listing = client.get("/me/bookmarks", headers=_auth(reader_token))
    assert listing.json() == []


def test_favorites_are_idempotent_and_persist(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_token = _signup(client, "reader5@example.com")

    client.put(f"/me/favorites/{story_id}", headers=_auth(reader_token))
    client.put(f"/me/favorites/{story_id}", headers=_auth(reader_token))  # adding twice shouldn't duplicate

    listing = client.get("/me/favorites", headers=_auth(reader_token))
    assert len(listing.json()) == 1


def test_remove_favorite(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_token = _signup(client, "reader6@example.com")
    client.put(f"/me/favorites/{story_id}", headers=_auth(reader_token))

    remove_response = client.delete(f"/me/favorites/{story_id}", headers=_auth(reader_token))
    assert remove_response.status_code == 204

    listing = client.get("/me/favorites", headers=_auth(reader_token))
    assert listing.json() == []


def test_bookmarks_and_favorites_are_scoped_per_user(client):
    admin_token = _make_admin(client)
    story_id = _create_story(client, admin_token)
    reader_a = _signup(client, "readerA@example.com")
    reader_b = _signup(client, "readerB@example.com")

    client.put("/me/bookmarks", json={"story_id": story_id}, headers=_auth(reader_a))
    client.put(f"/me/favorites/{story_id}", headers=_auth(reader_a))

    b_bookmarks = client.get("/me/bookmarks", headers=_auth(reader_b))
    b_favorites = client.get("/me/favorites", headers=_auth(reader_b))
    assert b_bookmarks.json() == []
    assert b_favorites.json() == []
