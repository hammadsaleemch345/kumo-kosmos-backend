from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.deps import require_role
from app.models import Role, User
from app.schemas import UploadResponse
from app.storage import UploadRejected, save_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_cover_image(
    file: UploadFile,
    _user: User = Depends(require_role(Role.ADMIN, Role.OWNER)),
) -> UploadResponse:
    contents = await file.read()
    try:
        url = save_upload(file, contents)
    except UploadRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return UploadResponse(url=url)
