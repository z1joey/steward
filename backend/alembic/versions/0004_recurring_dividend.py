"""TC-01: recurring_expenses / recurring_occurrences / dividend_runs

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False, server_default="month"),
        sa.Column("is_fixed", sa.Boolean(), nullable=False),
        sa.Column("fixed_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('rent','utilities','wages')", name="ck_recurring_kind"),
        sa.CheckConstraint("period = 'month'", name="ck_recurring_period_month"),
        # Locked：wages 禁手填金额
        sa.CheckConstraint("kind <> 'wages' OR fixed_amount IS NULL", name="ck_recurring_wages_no_amount"),
        sa.CheckConstraint("fixed_amount IS NULL OR fixed_amount > 0", name="ck_recurring_fixed_amount_positive"),
    )
    op.create_index("ix_recurring_store", "recurring_expenses", ["store_id"])

    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("recurring_expense_id", sa.BigInteger(), nullable=False),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("ledger_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["recurring_expense_id"], ["recurring_expenses.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_recurring_occurrences_amount_positive"),
        sa.UniqueConstraint("recurring_expense_id", "period_month", name="ux_recurring_occurrences_rec_month"),
    )

    op.create_table(
        "dividend_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("memo", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("confirmed_by", sa.BigInteger(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ledger_entry_id", sa.BigInteger(), nullable=False),
        sa.Column("public_txn_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.ForeignKeyConstraint(["public_txn_id"], ["public_account_txns.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_dividend_runs_amount_positive"),
    )


def downgrade() -> None:
    op.drop_table("dividend_runs")
    op.drop_table("recurring_occurrences")
    op.drop_index("ix_recurring_store", table_name="recurring_expenses")
    op.drop_table("recurring_expenses")
