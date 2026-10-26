"""Initial GuardRAIL schema

Revision ID: 001
Revises:
Create Date: 2026-10-20

"""

from typing import Sequence, Union

import app.models  # noqa: F401
from app.database import Base
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
