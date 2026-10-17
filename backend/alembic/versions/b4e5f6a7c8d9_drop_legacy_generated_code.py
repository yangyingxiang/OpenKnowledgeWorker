"""drop legacy single-file generated_code table

Revision ID: b4e5f6a7c8d9
Revises: a7b3c9e1f456
Create Date: 2026-10-15 00:00:00.000000

The single-file code generator was superseded by the multi-file coding agent
(code_projects / code_files).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b4e5f6a7c8d9'
down_revision: Union[str, None] = 'a7b3c9e1f456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_generated_code_process_id', table_name='generated_code', if_exists=True)
    op.drop_table('generated_code')


def downgrade() -> None:
    op.create_table(
        'generated_code',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('processes.id'), nullable=False),
        sa.Column('pdd_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pdd_versions.id'), nullable=True),
        sa.Column('code_content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=20)),
        sa.Column('agent_log', postgresql.JSONB()),
        sa.Column('pdd_code_mapping', postgresql.JSONB()),
        sa.Column('status', sa.String(length=50)),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_generated_code_process_id', 'generated_code', ['process_id'])
