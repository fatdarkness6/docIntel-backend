from typing import TYPE_CHECKING

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.document_tag import document_tags



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

    processing_stage: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        default="queued",
    )

    processing_progress: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
    )

    status_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        default="Document queued for processing",
    )

    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    status_event_id: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
        nullable=False,
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

