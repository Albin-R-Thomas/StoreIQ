"""Initial session, message and Meta inbox storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("associate_id", sa.String(100), nullable=False),
        sa.Column("store_id", sa.String(100), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("home_card", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_table(
        "webhook_inbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("phone_number_id", sa.String(100), nullable=False),
        sa.Column("message_id", sa.String(512), nullable=False),
        sa.Column("sender", sa.String(50), nullable=False),
        sa.Column("message_type", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("phone_number_id", "message_id", name="uq_meta_message"),
    )
    op.create_index("ix_webhook_inbox_status", "webhook_inbox", ["status"])


def downgrade():
    op.drop_table("webhook_inbox")
    op.drop_table("messages")
    op.drop_table("sessions")
