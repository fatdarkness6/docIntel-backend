"""convert embedding to vector

Revision ID: 9c673041b100
Revises: 11d2fbad3fe7
Create Date: 2026-08-09 15:26:50.510842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c673041b100'
down_revision: Union[str, Sequence[str], None] = '11d2fbad3fe7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        ALTER TABLE document_chunks
        ALTER COLUMN embedding
        TYPE vector(512)
        USING embedding::vector(512)
    """)


def downgrade():
    op.execute("""
        ALTER TABLE document_chunks
        ALTER COLUMN embedding
        TYPE text
        USING embedding::text
    """)
