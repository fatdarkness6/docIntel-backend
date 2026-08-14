from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse


router = APIRouter()


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Tag name cannot be empty"
        )

    existing_tag = db.execute(
        select(Tag).where(
            Tag.user_id == current_user.id,
            Tag.name == name
        )
    ).scalar_one_or_none()

    if existing_tag:
        raise HTTPException(
            status_code=409,
            detail="Tag already exists"
        )

    tag = Tag(
        user_id=current_user.id,
        name=name
    )

    db.add(tag)
    db.commit()
    db.refresh(tag)

    return tag


@router.get(
    "",
    response_model=list[TagResponse]
)
def get_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.execute(
        select(Tag)
        .where(Tag.user_id == current_user.id)
        .order_by(Tag.name)
    ).scalars().all()