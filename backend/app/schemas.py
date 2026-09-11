from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt silently ignores/rejects anything past 72 bytes, so passwords are capped here
# rather than truncated later. Capped in characters, not just bytes, since a password
# full of multi-byte unicode could stay under 72 chars but still exceed 72 bytes.
MAX_PASSWORD_BYTES = 72


def _validate_password_byte_length(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return password


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    _validate_password = field_validator("password")(_validate_password_byte_length)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    session_token: str
    email: str
    role: str


class UserResponse(BaseModel):
    email: str
    role: str


class UploadResponse(BaseModel):
    url: str


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(min_length=1, max_length=300, pattern=r"^[a-z0-9-]+$")
    content: str = ""
    cover_url: str | None = None
    free_wall_marker: int | None = None
    paid_wall_marker: int | None = None
    is_published: bool = False


class StoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = None
    cover_url: str | None = None
    free_wall_marker: int | None = None
    paid_wall_marker: int | None = None
    is_published: bool | None = None


class StoryResponse(BaseModel):
    id: str
    title: str
    slug: str
    cover_url: str | None
    content: str
    free_wall_marker: int | None
    paid_wall_marker: int | None
    is_published: bool

    model_config = {"from_attributes": True}


class PublicStoryResponse(BaseModel):
    """What a reader actually receives when opening a story. `content` is already truncated
    server-side to whatever their role is entitled to — never the full text for a guest or free
    reader, regardless of what's in the database. `access_level` tells the frontend which paywall
    prompt to show, it carries no information the client could use to unlock more content itself.
    """

    id: str  # needed by the frontend for bookmarks/favorites, which key off the real story id
    title: str
    slug: str
    cover_url: str | None
    content: str
    access_level: str  # "guest" | "free" | "full"


class SubscriberResponse(BaseModel):
    id: str
    email: str
    role: str
    is_veteran_sub: bool
    is_active: bool

    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)

    _validate_new_password = field_validator("new_password")(_validate_password_byte_length)


class MessageResponse(BaseModel):
    message: str


class BookmarkCreate(BaseModel):
    story_id: str
    passage_text: str | None = Field(default=None, max_length=2000)


class BookmarkResponse(BaseModel):
    story_id: str
    story_title: str
    story_slug: str
    passage_text: str | None
    created_at: str


class FavoriteResponse(BaseModel):
    story_id: str
    story_title: str
    story_slug: str
    created_at: str


class SiteContentPageUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = ""


class SiteContentPageResponse(BaseModel):
    slug: str
    title: str
    content: str

    model_config = {"from_attributes": True}


class SubscriberImportSummaryResponse(BaseModel):
    created_free: int
    created_veteran: int
    already_existed: int


class PostImportSummaryResponse(BaseModel):
    imported: int
    updated: int
    skipped_non_story: int
    skipped_unpublished: int


class FullImportSummaryResponse(BaseModel):
    subscribers: SubscriberImportSummaryResponse
    posts: PostImportSummaryResponse
