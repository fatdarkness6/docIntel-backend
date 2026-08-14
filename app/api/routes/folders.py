from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.folder import Folder
from app.models.user import User
from app.schemas.folder import (
    FolderCreate,
    FolderResponse,
    FolderUpdate,
)


router = APIRouter()


@router.post(
    "",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED
)
def create_folder(
    data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Folder name cannot be empty"
        )

    folder = Folder(
        user_id=current_user.id,
        name=name
    )

    db.add(folder)
    db.commit()
    db.refresh(folder)

    return folder


@router.get(
    "",
    response_model=list[FolderResponse]
)
def get_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folders = db.execute(
        select(Folder)
        .where(
            Folder.user_id == current_user.id
        )
        .order_by(Folder.created_at.desc())
    ).scalars().all()

    return folders


@router.patch(
    "/{folder_id}",
    response_model=FolderResponse
)
def update_folder(
    folder_id: int,
    data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folder = db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=404,
            detail="Folder not found"
        )

    folder.name = data.name.strip()

    db.commit()
    db.refresh(folder)

    return folder


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folder = db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=404,
            detail="Folder not found"
        )

    db.delete(folder)
    db.commit()