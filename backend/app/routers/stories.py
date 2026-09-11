from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user_optional
from app.models import Role, Story, User
from app.schemas import PublicStoryResponse

router = APIRouter(prefix="/stories", tags=["stories"])


def _truncate_for_access(story: Story, user: User | None) -> tuple[str, str]:
    """The actual lockdown: decide server-side how much of `content` this caller gets, and never
    send more. A guest or free reader physically never receives the later paragraphs in the
    response body, there is nothing in the client for them to inspect their way around.
    """
    is_paid = user is not None and user.role in (Role.PAID, Role.ADMIN, Role.OWNER)
    if is_paid:
        return story.content, "full"

    is_free_sub = user is not None and user.role == Role.FREE
    if is_free_sub and story.paid_wall_marker is not None:
        return story.content[: story.paid_wall_marker], "free"

    if story.free_wall_marker is not None:
        return story.content[: story.free_wall_marker], "guest"

    return "", "guest"


@router.get("/{slug}", response_model=PublicStoryResponse)
def read_story(
    slug: str,
    db: DBSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> PublicStoryResponse:
    story = db.query(Story).filter(Story.slug == slug, Story.is_published.is_(True)).first()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Story not found")

    content, access_level = _truncate_for_access(story, user)
    return PublicStoryResponse(
        id=story.id,
        title=story.title,
        slug=story.slug,
        cover_url=story.cover_url,
        content=content,
        access_level=access_level,
    )
