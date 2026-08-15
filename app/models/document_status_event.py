from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentStatusEvent(Base):
    __tablename__ = "document_status_events"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "event_id",
            name="uq_document_status_events_document_event",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    event_id: Mapped[int] = mapped_column(
        BigInteger,
    )

    status: Mapped[str] = mapped_column(
        String(20),
    )

    stage: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    progress: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
