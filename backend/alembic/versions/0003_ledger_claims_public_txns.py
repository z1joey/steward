"""TB-01: ledger_entries / expense_claims / public_account_txns

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("memo", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("reverses_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("reversed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"]),
        sa.ForeignKeyConstraint(["reverses_entry_id"], ["ledger_entries.id"]),
        sa.ForeignKeyConstraint(["reversed_by_id"], ["ledger_entries.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("direction IN ('income','expense')", name="ck_ledger_entries_direction"),
        sa.CheckConstraint(
            "source_type IN ('manual','claim','payroll','dividend','recurring')",
            name="ck_ledger_entries_source_type",
        ),
    )
    op.create_index(
        "ix_ledger_entries_store_date",
        "ledger_entries",
        ["store_id", sa.text("entry_date DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_ledger_entries_source", "ledger_entries", ["store_id", "source_type"]
    )
    # 一行最多冲正一次 [C]
    op.create_index(
        "ux_ledger_entries_reverses",
        "ledger_entries",
        ["reverses_entry_id"],
        unique=True,
        postgresql_where=sa.text("reverses_entry_id IS NOT NULL"),
    )

    op.create_table(
        "expense_claims",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("memo", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.BigInteger(), nullable=False),
        sa.Column("decided_by", sa.BigInteger(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_entry_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_expense_claims_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending','posted','rejected')", name="ck_expense_claims_status"
        ),
    )
    op.create_index("ix_claims_store_status", "expense_claims", ["store_id", "status"])

    op.create_table(
        "public_account_txns",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("public_account_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("direction", sa.String(length=5), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("ledger_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["public_account_id"], ["public_accounts.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_public_account_txns_amount_positive"),
        sa.CheckConstraint("direction IN ('in','out')", name="ck_public_account_txns_direction"),
    )
    op.create_index(
        "ix_public_txns_store_time",
        "public_account_txns",
        ["store_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_public_txns_store_time", table_name="public_account_txns")
    op.drop_table("public_account_txns")
    op.drop_index("ix_claims_store_status", table_name="expense_claims")
    op.drop_table("expense_claims")
    op.drop_index("ux_ledger_entries_reverses", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_source", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_store_date", table_name="ledger_entries")
    op.drop_table("ledger_entries")
