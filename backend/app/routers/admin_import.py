import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_role
from app.importer.zip_import import run_subscriber_only_import, run_substack_import
from app.models import Role, User
from app.schemas import (
    FullImportSummaryResponse,
    PostImportSummaryResponse,
    SubscriberImportSummaryResponse,
)

router = APIRouter(prefix="/admin/import", tags=["admin-import"])

_STAFF = (Role.ADMIN, Role.OWNER)


@router.post("/full", response_model=FullImportSummaryResponse)
async def import_full_export(
    file: UploadFile,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> FullImportSummaryResponse:
    """Upload the full Substack export ZIP. Safe to re-run any time — matches existing posts by
    substack_post_id and subscribers by email, so nothing gets duplicated on a second run.
    """
    if not (file.filename or "").endswith(".zip"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Expected a .zip export file")

    contents = await file.read()
    try:
        result = run_substack_import(db, io.BytesIO(contents))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    return FullImportSummaryResponse(
        subscribers=SubscriberImportSummaryResponse(**vars(result.subscribers)),
        posts=PostImportSummaryResponse(**vars(result.posts)),
    )


@router.post("/subscribers", response_model=SubscriberImportSummaryResponse)
async def import_subscribers_only(
    file: UploadFile,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> SubscriberImportSummaryResponse:
    """Upload just the subscriber CSV (email_list*.csv from a Substack export), without the
    full ZIP. Meant to be re-run any time as a backup path — posts only need importing once,
    but the subscriber list may need re-importing if the current platform ever goes down.
    """
    if not (file.filename or "").endswith(".csv"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Expected a .csv file")

    contents = await file.read()
    summary = run_subscriber_only_import(db, contents.decode("utf-8"))
    return SubscriberImportSummaryResponse(**vars(summary))
