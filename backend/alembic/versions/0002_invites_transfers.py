"""TA-02: invites / transfers（[Open O-08] 最小字段 Convention）

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("inviter_user_id", sa.BigInteger(), nullable=False),
        sa.Column("invitee_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="store_manager"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invitee_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role = 'store_manager'", name="ck_invites_role"),
        sa.CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_invites_status"),
    )
    # [C] 同一人同店一份待接受；不同人可并行多份（店长不限）
    op.create_index(
        "ux_invites_one_pending_per_invitee",
        "invites",
        ["store_id", "invitee_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_invites_invitee", "invites", ["invitee_user_id", "status"])

    op.create_table(
        "transfers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("from_user_id", sa.BigInteger(), nullable=False),
        sa.Column("to_user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('pending','accepted')", name="ck_transfers_status"),
    )
    op.create_index(
        "ux_transfers_one_pending_per_store",
        "transfers",
        ["store_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_transfers_to", "transfers", ["to_user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_transfers_to", table_name="transfers")
    op.drop_index("ux_transfers_one_pending_per_store", table_name="transfers")
    op.drop_table("transfers")
    op.drop_index("ix_invites_invitee", table_name="invites")
    op.drop_index("ux_invites_one_pending_per_invitee", table_name="invites")
    op.drop_table("invites")
