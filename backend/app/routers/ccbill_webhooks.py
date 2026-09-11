from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.ccbill import resolve_subscription_status
from app.config import settings
from app.database import get_db
from app.models import PaymentEvent, Role, User
from app.security import utcnow

router = APIRouter(prefix="/webhooks/ccbill", tags=["ccbill-webhooks"])


def _log_event(db: DBSession, form: dict) -> PaymentEvent | None:
    """Always record the raw event first, regardless of whether we can act on it. Returns None
    if this exact event was already logged (CCBill retries webhooks on anything but a 200), so
    the caller can skip re-processing instead of double-applying a state change.
    """
    event = PaymentEvent(
        ccbill_subscription_id=form.get("subscriptionId", ""),
        event_type=form.get("eventType", ""),
        ccbill_timestamp=form.get("timestamp", ""),
        raw_payload=str(dict(form)),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(event)
    return event


def _apply_subscription_status(db: DBSession, event: PaymentEvent) -> None:
    new_status = resolve_subscription_status(event.event_type)
    if new_status is None:
        return  # unrecognized event type; logged above, nothing to apply

    user = db.query(User).filter(User.ccbill_subscription_id == event.ccbill_subscription_id).first()
    if user is None:
        return  # subscription not yet linked to a user; the raw event is still on record

    user.subscription_status = new_status
    user.role = Role.PAID if new_status.value == "active" else user.role
    event.processed_at = utcnow()
    db.commit()


@router.post("", status_code=status.HTTP_200_OK)
async def receive_ccbill_webhook(
    request: Request,
    secret: str = "",
    db: DBSession = Depends(get_db),
) -> dict[str, str]:
    if not settings.ccbill_webhook_secret or secret != settings.ccbill_webhook_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")

    form = dict(await request.form())
    event = _log_event(db, form)
    if event is not None:
        _apply_subscription_status(db, event)

    # Always 200, even for a duplicate/unrecognized event, so CCBill stops retrying it.
    return {"status": "received"}
