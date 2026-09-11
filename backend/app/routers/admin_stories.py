from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import require_role
from app.models import Role, Story, User
from app.schemas import StoryCreate, StoryResponse, StoryUpdate

router = APIRouter(prefix="/admin/stories", tags=["admin-stories"])

_STAFF = (Role.ADMIN, Role.OWNER)


@router.get("", response_model=list[StoryResponse])
def list_stories(
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> list[Story]:
    return db.query(Story).order_by(Story.created_at.desc()).all()


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    payload: StoryCreate,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> Story:
    if db.query(Story).filter(Story.slug == payload.slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "A story with this slug already exists")

    story = Story(**payload.model_dump())
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def _get_story_or_404(story_id: str, db: DBSession) -> Story:
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Story not found")
    return story


@router.patch("/{story_id}", response_model=StoryResponse)
def update_story(
    story_id: str,
    payload: StoryUpdate,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> Story:
    story = _get_story_or_404(story_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(story, field, value)
    db.commit()
    db.refresh(story)
    return story


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: str,
    db: DBSession = Depends(get_db),
    _user: User = Depends(require_role(*_STAFF)),
) -> None:
    story = _get_story_or_404(story_id, db)
    db.delete(story)
    db.commit()
