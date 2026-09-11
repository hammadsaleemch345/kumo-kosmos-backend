import uuid
from pathlib import Path

from fastapi import UploadFile

# Client hasn't decided between S3/Cloudinary/self-hosted yet (open kickoff question).
# Local disk keeps development unblocked either way; swapping the backend later only
# means changing save_upload's body, callers never touch the filesystem directly.
_UPLOAD_ROOT = Path("uploads")
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UploadRejected(Exception):
    pass


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise UploadRejected(f"Unsupported file type '{suffix}', allowed: {sorted(_ALLOWED_EXTENSIONS)}")
    return suffix


def save_upload(file: UploadFile, contents: bytes) -> str:
    """Save an uploaded cover/image and return its public URL path.

    contents is passed in explicitly (rather than re-reading file) so callers can enforce the
    size limit before this ever touches disk.
    """
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise UploadRejected(f"File exceeds the {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")

    suffix = _validate_extension(file.filename or "")
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{suffix}"
    (_UPLOAD_ROOT / stored_name).write_bytes(contents)
    return f"/uploads/{stored_name}"
