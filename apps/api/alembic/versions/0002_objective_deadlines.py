"""Add objective deadlines and event retention index.

Revision ID: 0002_objective_deadlines
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_objective_deadlines"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    round_columns = {column["name"] for column in inspector.get_columns("quest_rounds")}
    if "objective_duration_seconds" not in round_columns:
        op.add_column(
            "quest_rounds",
            sa.Column("objective_duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("120")),
        )
        op.alter_column("quest_rounds", "objective_duration_seconds", server_default=None)
    if "objective_ends_at" not in round_columns:
        op.add_column("quest_rounds", sa.Column("objective_ends_at", sa.DateTime(timezone=True), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("processed_events")}
    if "ix_processed_events_processed_at" not in indexes:
        op.create_index("ix_processed_events_processed_at", "processed_events", ["processed_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    round_columns = {column["name"] for column in inspector.get_columns("quest_rounds")}
    if "objective_ends_at" in round_columns:
        op.drop_column("quest_rounds", "objective_ends_at")
    if "objective_duration_seconds" in round_columns:
        op.drop_column("quest_rounds", "objective_duration_seconds")

    indexes = {index["name"] for index in inspector.get_indexes("processed_events")}
    if "ix_processed_events_processed_at" in indexes:
        op.drop_index("ix_processed_events_processed_at", table_name="processed_events")
