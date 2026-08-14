from fastapi import APIRouter
from app.api.routes import health, auth , documents , folders , tags


api_router = APIRouter()

api_router.include_router(
    health.router,
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"]
)

api_router.include_router(
    folders.router,
    prefix="/folders",
    tags=["Folders"]
)

api_router.include_router(
    tags.router,
    prefix="/tags",
    tags=["Tags"]
)