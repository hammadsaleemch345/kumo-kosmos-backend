import pytest

from app.ccbill import CCBillNotConfigured, build_checkout_url, resolve_subscription_status
from app.models import PaymentEvent, Role, SubscriptionStatus, User


def test_build_checkout_url_fails_loudly_without_account_config():
    with pytest.raises(CCBillNotConfigured):
        build_checkout_url(price_cents=2000, period_days=30)


def test_build_checkout_url_with_config(monkeypatch):
    monkeypatch.setattr("app.ccbill.settings.ccbill_client_account", "123456")
    monkeypatch.setattr("app.ccbill.settings.ccbill_client_subaccount", "0000")
    monkeypatch.setattr("app.ccbill.settings.ccbill_dynamic_pricing_salt", "test-salt")

    url = build_checkout_url(price_cents=2000, period_days=30)

    assert "clientSubacc=0000" in url
    assert "initialPrice=20.00" in url
    assert "formDigest=" in url


def test_resolve_subscription_status_known_events():
    assert resolve_subscription_status("NewSaleSuccess") == SubscriptionStatus.ACTIVE
    assert resolve_subscription_status("Cancellation") == SubscriptionStatus.CANCELLED
    assert resolve_subscription_status("Chargeback") == SubscriptionStatus.CHARGEBACK


def test_resolve_subscription_status_unknown_event_returns_none():
    assert resolve_subscription_status("SomeFutureEventCCBillAddsLater") is None


def test_webhook_rejects_missing_or_wrong_secret(client, monkeypatch):
    monkeypatch.setattr("app.routers.ccbill_webhooks.settings.ccbill_webhook_secret", "correct-secret")

    response = client.post(
        "/webhooks/ccbill",
        params={"secret": "wrong-secret"},
        data={"eventType": "NewSaleSuccess", "subscriptionId": "sub_1", "timestamp": "1"},
    )

    assert response.status_code == 401


def test_webhook_accepts_and_updates_subscription_status(client, monkeypatch):
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr("app.routers.ccbill_webhooks.settings.ccbill_webhook_secret", "correct-secret")

    db = TestingSessionLocal()
    db.add(User(email="paying@example.com", password_hash=None, ccbill_subscription_id="sub_1"))
    db.commit()
    db.close()

    response = client.post(
        "/webhooks/ccbill",
        params={"secret": "correct-secret"},
        data={"eventType": "NewSaleSuccess", "subscriptionId": "sub_1", "timestamp": "1000"},
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "paying@example.com").first()
    assert user.subscription_status == SubscriptionStatus.ACTIVE
    assert user.role == Role.PAID
    assert db.query(PaymentEvent).count() == 1
    db.close()


def test_webhook_is_idempotent_on_exact_duplicate_event(client, monkeypatch):
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr("app.routers.ccbill_webhooks.settings.ccbill_webhook_secret", "correct-secret")
    payload = {"eventType": "NewSaleSuccess", "subscriptionId": "sub_2", "timestamp": "2000"}

    client.post("/webhooks/ccbill", params={"secret": "correct-secret"}, data=payload)
    second_response = client.post("/webhooks/ccbill", params={"secret": "correct-secret"}, data=payload)

    assert second_response.status_code == 200  # still 200, so CCBill doesn't keep retrying

    db = TestingSessionLocal()
    assert db.query(PaymentEvent).filter(PaymentEvent.ccbill_subscription_id == "sub_2").count() == 1
    db.close()


def test_webhook_logs_event_even_when_no_matching_user_exists(client, monkeypatch):
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr("app.routers.ccbill_webhooks.settings.ccbill_webhook_secret", "correct-secret")

    response = client.post(
        "/webhooks/ccbill",
        params={"secret": "correct-secret"},
        data={"eventType": "NewSaleSuccess", "subscriptionId": "unlinked_sub", "timestamp": "3000"},
    )

    assert response.status_code == 200

    db = TestingSessionLocal()
    event = db.query(PaymentEvent).filter(PaymentEvent.ccbill_subscription_id == "unlinked_sub").first()
    assert event is not None
    assert event.processed_at is None  # logged, but never applied since no user was linked
    db.close()


def test_webhook_with_unrecognized_event_type_is_logged_but_not_applied(client, monkeypatch):
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr("app.routers.ccbill_webhooks.settings.ccbill_webhook_secret", "correct-secret")

    db = TestingSessionLocal()
    db.add(User(email="mystery@example.com", password_hash=None, ccbill_subscription_id="sub_3"))
    db.commit()
    db.close()

    response = client.post(
        "/webhooks/ccbill",
        params={"secret": "correct-secret"},
        data={"eventType": "SomethingCCBillMightAddLater", "subscriptionId": "sub_3", "timestamp": "4000"},
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "mystery@example.com").first()
    assert user.subscription_status == SubscriptionStatus.NONE  # untouched
    db.close()
