from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_role
from app.models import Role, SiteContentPage, User
from app.schemas import SiteContentPageResponse, SiteContentPageUpdate

public_router = APIRouter(prefix="/pages", tags=["pages"])
admin_router = APIRouter(prefix="/admin/pages", tags=["admin-pages"])


@public_router.get("/{slug}", response_model=SiteContentPageResponse)
def read_page(slug: str, db: DBSession = Depends(get_db)) -> SiteContentPage:
    page = db.query(SiteContentPage).filter(SiteContentPage.slug == slug).first()
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")
    return page


@admin_router.put("/{slug}", response_model=SiteContentPageResponse)
def upsert_page(
    slug: str,
    payload: SiteContentPageUpdate,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(Role.ADMIN, Role.OWNER)),
) -> SiteContentPage:
    page = db.query(SiteContentPage).filter(SiteContentPage.slug == slug).first()
    if page is None:
        page = SiteContentPage(slug=slug, title=payload.title, content=payload.content)
        db.add(page)
    else:
        page.title = payload.title
        page.content = payload.content
    db.commit()
    db.refresh(page)
    return page
