from datetime import datetime

from pydantic import BaseModel


class FolderCreate(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class FolderUpdate(BaseModel):
    name: str