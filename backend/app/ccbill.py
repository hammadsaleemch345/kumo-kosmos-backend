import hashlib

from app.config import settings
from app.models import SubscriptionStatus

# CCBill's own event type names for its DataLink webhook push, confirmed from CCBill's published
# integration docs. Mapped to our internal subscription states (active/past_due/cancelled/chargeback)
# so the rest of the app never has to know CCBill's vocabulary, only ours.
EVENT_TYPE_TO_STATUS: dict[str, SubscriptionStatus] = {
    "NewSaleSuccess": SubscriptionStatus.ACTIVE,
    "RenewalSuccess": SubscriptionStatus.ACTIVE,
    "Cancellation": SubscriptionStatus.CANCELLED,
    "Expiration": SubscriptionStatus.CANCELLED,
    "RenewalFailure": SubscriptionStatus.PAST_DUE,
    "VoidSale": SubscriptionStatus.CANCELLED,
    "Refund": SubscriptionStatus.CANCELLED,
    "Chargeback": SubscriptionStatus.CHARGEBACK,
}


class CCBillNotConfigured(Exception):
    pass


def _require_config() -> None:
    if not (settings.ccbill_client_account and settings.ccbill_dynamic_pricing_salt):
        raise CCBillNotConfigured(
            "CCBill client account / dynamic pricing salt not set. "
            "These come from the client's CCBill merchant account and haven't been provided yet "
            "(tracked as an open item in context.md) — cannot build a real checkout URL without them."
        )


def build_checkout_url(price_cents: int, period_days: int, currency_code: str = "840") -> str:
    """Build a CCBill FlexForms dynamic-pricing checkout URL.

    The digest formula (price + period + currencyCode + salt, MD5) is CCBill's documented dynamic
    pricing signature. NOTE: this has not been verified against the client's actual CCBill account
    yet — confirm exact param formatting (price as cents vs dollars, form ID, etc.) once account
    access is available, before this is used for a real charge.
    """
    _require_config()
    price = f"{price_cents / 100:.2f}"
    digest_input = f"{price}{period_days}{currency_code}{settings.ccbill_dynamic_pricing_salt}"
    form_digest = hashlib.md5(digest_input.encode()).hexdigest()

    return (
        "https://api.ccbill.com/wap-frontflex/flexforms/"
        f"{settings.ccbill_client_account}?"
        f"clientSubacc={settings.ccbill_client_subaccount}"
        f"&initialPrice={price}&initialPeriod={period_days}"
        f"&currencyCode={currency_code}&formDigest={form_digest}"
    )


def resolve_subscription_status(event_type: str) -> SubscriptionStatus | None:
    """Return None for an event type we don't recognize, rather than guessing, so an unmapped
    CCBill event gets logged (PaymentEvent always records the raw payload) without silently
    corrupting a subscriber's state.
    """
    return EVENT_TYPE_TO_STATUS.get(event_type)
