from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, BigInteger, func , Boolean
from sqlalchemy.orm import Mapped, mapped_column , relationship
from app.models.document_tag import document_tags
from sqlalchemy import Text
from typing import TYPE_CHECKING
from app.db.session import Base



if TYPE_CHECKING:
    from app.models.tag import Tag

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    filename: Mapped[str] = mapped_column(
        String(255)
    )

    stored_name: Mapped[str] = mapped_column(
        String(255)
    )

    file_type: Mapped[str] = mapped_column(
        String(20)
    )

    size_bytes: Mapped[int] = mapped_column(
        BigInteger
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    insights: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing"
    )
    
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "folders.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=document_tags,
        back_populates="documents"
    )

