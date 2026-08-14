from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.db.session import Base
from app.models.document_tag import document_tags



if TYPE_CHECKING:
    from app.models.document import Document

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        )
    )

    name: Mapped[str] = mapped_column(
        String(50)
    )

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_tags,
        back_populates="tags"
    )