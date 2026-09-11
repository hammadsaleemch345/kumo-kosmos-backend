from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Bookmark, Favorite, Story, User
from app.schemas import BookmarkCreate, BookmarkResponse, FavoriteResponse

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/bookmarks", response_model=list[BookmarkResponse])
def list_bookmarks(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BookmarkResponse]:
    rows = db.query(Bookmark, Story).join(Story, Bookmark.story_id == Story.id).filter(Bookmark.user_id == user.id)
    return [
        BookmarkResponse(
            story_id=story.id,
            story_title=story.title,
            story_slug=story.slug,
            passage_text=bookmark.passage_text,
            created_at=bookmark.created_at.isoformat(),
        )
        for bookmark, story in rows
    ]


@router.put("/bookmarks", response_model=BookmarkResponse)
def upsert_bookmark(
    payload: BookmarkCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookmarkResponse:
    """One bookmark per user per story — saving again just updates the passage, doesn't duplicate."""
    story = db.query(Story).filter(Story.id == payload.story_id).first()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Story not found")

    bookmark = db.query(Bookmark).filter(Bookmark.user_id == user.id, Bookmark.story_id == story.id).first()
    if bookmark is None:
        bookmark = Bookmark(user_id=user.id, story_id=story.id)
        db.add(bookmark)
    bookmark.passage_text = payload.passage_text
    db.commit()
    db.refresh(bookmark)

    return BookmarkResponse(
        story_id=story.id,
        story_title=story.title,
        story_slug=story.slug,
        passage_text=bookmark.passage_text,
        created_at=bookmark.created_at.isoformat(),
    )


@router.delete("/bookmarks/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    story_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    db.query(Bookmark).filter(Bookmark.user_id == user.id, Bookmark.story_id == story_id).delete()
    db.commit()


@router.get("/favorites", response_model=list[FavoriteResponse])
def list_favorites(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FavoriteResponse]:
    rows = db.query(Favorite, Story).join(Story, Favorite.story_id == Story.id).filter(Favorite.user_id == user.id)
    return [
        FavoriteResponse(
            story_id=story.id,
            story_title=story.title,
            story_slug=story.slug,
            created_at=favorite.created_at.isoformat(),
        )
        for favorite, story in rows
    ]


@router.put("/favorites/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(
    story_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Story not found")

    exists = db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.story_id == story_id).first()
    if exists is None:
        db.add(Favorite(user_id=user.id, story_id=story_id))
        db.commit()


@router.delete("/favorites/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    story_id: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    db.query(Favorite).filter(Favorite.user_id == user.id, Favorite.story_id == story_id).delete()
    db.commit()
