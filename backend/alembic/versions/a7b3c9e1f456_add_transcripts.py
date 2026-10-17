"""add_transcripts

Revision ID: a7b3c9e1f456
Revises: c662f5f3e255
Create Date: 2026-04-03 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b3c9e1f456'
down_revision: Union[str, None] = 'c662f5f3e255'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('transcripts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('process_id', sa.UUID(), nullable=False),
    sa.Column('session_key', sa.String(length=255), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('entry_type', sa.String(length=30), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('tool_name', sa.String(length=100), nullable=True),
    sa.Column('tool_input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tool_output', sa.Text(), nullable=True),
    sa.Column('token_input', sa.Integer(), nullable=True),
    sa.Column('token_output', sa.Integer(), nullable=True),
    sa.Column('duration_ms', sa.Float(), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['process_id'], ['processes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcripts_process_id'), 'transcripts', ['process_id'], unique=False)
    op.create_index(op.f('ix_transcripts_session_key'), 'transcripts', ['session_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transcripts_session_key'), table_name='transcripts')
    op.drop_index(op.f('ix_transcripts_process_id'), table_name='transcripts')
    op.drop_table('transcripts')
