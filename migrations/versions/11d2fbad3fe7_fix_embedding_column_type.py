"""fix embedding column type

Revision ID: 11d2fbad3fe7
Revises: 4ffc370907c2
Create Date: 2026-08-09 15:20:39.225288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11d2fbad3fe7'
down_revision: Union[str, Sequence[str], None] = '4ffc370907c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
