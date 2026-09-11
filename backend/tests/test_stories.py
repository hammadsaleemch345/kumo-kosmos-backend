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


def _create_published_story(client, admin_token):
    guest_text = "This is the free preview everyone can see. "
    free_text = "This is the free-subscriber bonus section. "
    paid_text = "This is the paid-only content, the actual point of the story."
    content = guest_text + free_text + paid_text

    payload = {
        "title": "A Locked Story",
        "slug": "a-locked-story",
        "content": content,
        "free_wall_marker": len(guest_text),
        "paid_wall_marker": len(guest_text) + len(free_text),
        "is_published": True,
    }
    client.post("/admin/stories", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    return guest_text, free_text, paid_text


def _make_admin(client):
    return _signup_with_role(client, "admin@example.com", Role.ADMIN)


def test_guest_never_receives_paid_or_free_bonus_text_in_the_response_body(client):
    admin_token = _make_admin(client)
    guest_text, free_text, paid_text = _create_published_story(client, admin_token)

    response = client.get("/stories/a-locked-story")

    assert response.status_code == 200
    body = response.json()
    assert body["access_level"] == "guest"
    assert guest_text in body["content"]
    assert free_text not in body["content"]
    assert paid_text not in body["content"]


def test_free_subscriber_gets_bonus_section_but_never_paid_text(client):
    admin_token = _make_admin(client)
    guest_text, free_text, paid_text = _create_published_story(client, admin_token)
    free_token = _signup_with_role(client, "freereader@example.com", Role.FREE)

    response = client.get("/stories/a-locked-story", headers={"Authorization": f"Bearer {free_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_level"] == "free"
    assert guest_text in body["content"]
    assert free_text in body["content"]
    assert paid_text not in body["content"]


def test_paid_subscriber_gets_the_full_story(client):
    admin_token = _make_admin(client)
    guest_text, free_text, paid_text = _create_published_story(client, admin_token)
    paid_token = _signup_with_role(client, "paidreader@example.com", Role.PAID)

    response = client.get("/stories/a-locked-story", headers={"Authorization": f"Bearer {paid_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_level"] == "full"
    assert guest_text in body["content"]
    assert free_text in body["content"]
    assert paid_text in body["content"]


def test_guest_with_garbage_bearer_token_is_still_treated_as_guest_not_errored(client):
    admin_token = _make_admin(client)
    _create_published_story(client, admin_token)

    response = client.get("/stories/a-locked-story", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 200
    assert response.json()["access_level"] == "guest"


def test_unpublished_story_404s_even_for_a_paid_subscriber(client):
    admin_token = _make_admin(client)
    payload = {
        "title": "Draft Story",
        "slug": "draft-story",
        "content": "not ready yet",
        "is_published": False,
    }
    client.post("/admin/stories", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    paid_token = _signup_with_role(client, "paidreader2@example.com", Role.PAID)

    response = client.get("/stories/draft-story", headers={"Authorization": f"Bearer {paid_token}"})

    assert response.status_code == 404


def test_unknown_slug_404s(client):
    response = client.get("/stories/this-does-not-exist")

    assert response.status_code == 404
