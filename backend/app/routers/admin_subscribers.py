from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_role
from app.models import Role, User
from app.schemas import SubscriberResponse

router = APIRouter(prefix="/admin/subscribers", tags=["admin-subscribers"])


@router.get("", response_model=list[SubscriberResponse])
def list_subscribers(
    search: str = "",
    veteran_only: bool = False,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(Role.ADMIN, Role.OWNER)),
) -> list[User]:
    query = db.query(User)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    if veteran_only:
        query = query.filter(User.is_veteran_sub.is_(True))
    return query.order_by(User.created_at.desc()).all()
