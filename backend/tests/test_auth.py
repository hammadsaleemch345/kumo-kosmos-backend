def _signup(client, email="reader@example.com", password="hunter2pass"):
    return client.post("/auth/signup", json={"email": email, "password": password})


def test_signup_creates_account_and_returns_session_token(client):
    response = _signup(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "reader@example.com"
    assert body["role"] == "free"
    assert body["session_token"]


def test_signup_rejects_duplicate_email(client):
    _signup(client)
    response = _signup(client)

    assert response.status_code == 409


def test_signup_rejects_short_password(client):
    response = _signup(client, password="short")

    assert response.status_code == 422


def test_login_with_correct_credentials_returns_session_token(client):
    _signup(client)

    response = client.post("/auth/login", json={"email": "reader@example.com", "password": "hunter2pass"})

    assert response.status_code == 200
    assert response.json()["session_token"]


def test_login_with_wrong_password_is_rejected(client):
    _signup(client)

    response = client.post("/auth/login", json={"email": "reader@example.com", "password": "wrongpass"})

    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client):
    response = client.post("/auth/login", json={"email": "ghost@example.com", "password": "hunter2pass"})

    assert response.status_code == 401


def test_logout_revokes_the_session(client):
    token = _signup(client).json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 200

    # A revoked session should no longer authenticate future requests.
    second_logout = client.post("/auth/logout", headers=headers)
    assert second_logout.status_code == 401


def test_logout_without_a_session_token_is_rejected(client):
    response = client.post("/auth/logout")

    assert response.status_code == 401


def test_password_reset_request_returns_generic_message_for_unknown_email(client):
    response = client.post("/auth/password-reset/request", json={"email": "ghost@example.com"})

    assert response.status_code == 200
    assert "if that email is registered" in response.json()["message"].lower()


def test_password_reset_confirm_rejects_invalid_token(client):
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "brandnewpass1"},
    )

    assert response.status_code == 400


def test_full_password_reset_flow_lets_user_log_in_with_new_password(client, monkeypatch):
    _signup(client)

    captured = {}
    from app import security

    original_generate_token = security.generate_token

    def _capture_generate_token():
        raw_token, token_hash = original_generate_token()
        captured["raw_token"] = raw_token
        return raw_token, token_hash

    monkeypatch.setattr("app.routers.auth.generate_token", _capture_generate_token)

    client.post("/auth/password-reset/request", json={"email": "reader@example.com"})
    reset_token = captured["raw_token"]

    confirm_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "brandnewpass1"},
    )
    assert confirm_response.status_code == 200

    old_password_login = client.post(
        "/auth/login", json={"email": "reader@example.com", "password": "hunter2pass"}
    )
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/auth/login", json={"email": "reader@example.com", "password": "brandnewpass1"}
    )
    assert new_password_login.status_code == 200


def test_signup_rejects_malformed_email(client):
    response = _signup(client, email="not-an-email")

    assert response.status_code == 422


def test_signup_normalizes_email_case_so_duplicates_cant_slip_through(client):
    _signup(client, email="Reader@Example.com")

    response = _signup(client, email="reader@example.com")

    assert response.status_code == 409


def test_login_is_case_insensitive_on_email(client):
    _signup(client, email="Reader@Example.com")

    response = client.post("/auth/login", json={"email": "reader@EXAMPLE.com", "password": "hunter2pass"})

    assert response.status_code == 200


def test_signup_rejects_password_over_72_bytes(client):
    response = _signup(client, password="x" * 73)

    assert response.status_code == 422


def test_signup_rejects_password_over_72_bytes_via_multibyte_chars(client):
    # 25 chars but each euro sign is 3 bytes in UTF-8, so this is 75 bytes despite being under the 72 char cap
    response = _signup(client, password="€" * 25)

    assert response.status_code == 422


def test_me_returns_current_user_for_a_valid_session(client):
    token = _signup(client).json()["session_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"email": "reader@example.com", "role": "free"}


def test_me_rejects_missing_authorization_header(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_malformed_authorization_header(client):
    response = client.get("/auth/me", headers={"Authorization": "not-a-bearer-token"})

    assert response.status_code == 401


def test_me_rejects_garbage_bearer_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer totally-made-up-token"})

    assert response.status_code == 401


def test_me_rejects_revoked_session(client):
    token = _signup(client).json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/logout", headers=headers)

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_me_rejects_expired_session(client):
    token = _signup(client).json()["session_token"]

    from datetime import timedelta

    from app.security import hash_token, utcnow
    from tests.conftest import TestingSessionLocal
    from app.models import Session as SessionModel

    db = TestingSessionLocal()
    session = db.query(SessionModel).filter(SessionModel.token_hash == hash_token(token)).first()
    session.expires_at = utcnow() - timedelta(hours=1)
    db.commit()
    db.close()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_password_reset_token_cannot_be_reused(client, monkeypatch):
    _signup(client)

    captured = {}
    from app import security

    original_generate_token = security.generate_token

    def _capture_generate_token():
        raw_token, token_hash = original_generate_token()
        captured["raw_token"] = raw_token
        return raw_token, token_hash

    monkeypatch.setattr("app.routers.auth.generate_token", _capture_generate_token)

    client.post("/auth/password-reset/request", json={"email": "reader@example.com"})
    reset_token = captured["raw_token"]

    client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "brandnewpass1"},
    )
    second_attempt = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "anotherpass2"},
    )

    assert second_attempt.status_code == 400
