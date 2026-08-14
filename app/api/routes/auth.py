from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse ,  UserLogin, TokenResponse
from app.core.security import hash_password , verify_password, create_access_token
from app.api.dependencies import get_current_user


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    statement = select(User).where(
        User.email == data.email
    )

    existing_user = db.execute(statement).scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    user = User(
        email=data.email,
        password_hash=hash_password(data.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.execute(
        select(User).where(
            User.email == form_data.username
        )
    ).scalar_one_or_none()

    if not user or not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user