"""004_add_deep_analysis_fields

Revision ID: a1b2c3d4e5f6
Revises: e770506d9786
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e770506d9786"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trend: add relevance_reason
    op.add_column("trends", sa.Column("relevance_reason", sa.String(length=200), nullable=True))

    # AIInsight: add deep analysis fields
    op.add_column("ai_insights", sa.Column("search_context", sa.Text(), nullable=True))
    op.add_column("ai_insights", sa.Column("deep_analysis", sa.Text(), nullable=True))
    op.add_column("ai_insights", sa.Column("source_urls", sa.Text(), nullable=True))
    op.add_column("ai_insights", sa.Column("analysis_type", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_insights", "analysis_type")
    op.drop_column("ai_insights", "source_urls")
    op.drop_column("ai_insights", "deep_analysis")
    op.drop_column("ai_insights", "search_context")
    op.drop_column("trends", "relevance_reason")
