from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentQuestion(Base):
    __tablename__ = "document_questions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey(
        "documents.id",
        ondelete="CASCADE"
        )
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    question: Mapped[str] = mapped_column(
        Text
    )

    answer: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )