from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR

from app.db.session import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    chunk_index: Mapped[int] = mapped_column()

    content: Mapped[str] = mapped_column(
        Text
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(512),
        nullable=True
    )

    page_number: Mapped[int | None] = mapped_column(
        nullable=True
    )