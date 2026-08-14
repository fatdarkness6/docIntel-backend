from sqlalchemy import Column, ForeignKey, Table

from app.db.session import Base


document_tags = Table(
    "document_tags",
    Base.metadata,

    Column(
        "document_id",
        ForeignKey(
            "documents.id",
            ondelete="CASCADE"
        ),
        primary_key=True
    ),

    Column(
        "tag_id",
        ForeignKey(
            "tags.id",
            ondelete="CASCADE"
        ),
        primary_key=True
    )
)