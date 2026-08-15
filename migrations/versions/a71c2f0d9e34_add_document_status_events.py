"""add document status events

Revision ID: a71c2f0d9e34
Revises: 9b3684aa3acb
Create Date: 2026-08-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a71c2f0d9e34"
down_revision: Union[str, Sequence[str], None] = "9b3684aa3acb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processing_stage", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processing_progress", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("status_message", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "status_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "status_event_id",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )

    op.create_table(
        "document_status_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "event_id",
            name="uq_document_status_events_document_event",
        ),
    )
    op.create_index(
        op.f("ix_document_status_events_document_id"),
        "document_status_events",
        ["document_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE documents
        SET processing_stage = CASE
                WHEN status = 'completed' THEN 'completed'
                WHEN status = 'failed' THEN 'failed'
                ELSE 'queued'
            END,
            processing_progress = CASE
                WHEN status = 'completed' THEN 100
                WHEN status = 'processing' THEN 0
                ELSE NULL
            END,
            status_message = CASE
                WHEN status = 'completed' THEN 'Document processing completed'
                WHEN status = 'failed' THEN 'Document processing failed'
                ELSE 'Document queued for processing'
            END,
            status_event_id = 1
        """
    )
    op.execute(
        """
        INSERT INTO document_status_events
            (document_id, event_id, status, stage, progress, message, updated_at)
        SELECT id, status_event_id, status, processing_stage,
               processing_progress, status_message, status_updated_at
        FROM documents
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_status_events_document_id"),
        table_name="document_status_events",
    )
    op.drop_table("document_status_events")
    op.drop_column("documents", "status_event_id")
    op.drop_column("documents", "status_updated_at")
    op.drop_column("documents", "status_message")
    op.drop_column("documents", "processing_progress")
    op.drop_column("documents", "processing_stage")
