"""TD-01: employees / employee_leaves / shift_segments / payroll_runs / payroll_lines

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("contact", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("job_type", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("resigned_on", sa.Date(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "job_type IN ('long_term','summer','winter','weekend','temporary')",
            name="ck_employees_job_type",
        ),
        sa.CheckConstraint(
            "(status = 'resigned') = (resigned_on IS NOT NULL)",
            name="ck_employees_resigned_pair",
        ),
    )
    op.create_index("ix_employees_store", "employees", ["store_id"])

    op.create_table(
        "employee_leaves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("end_date >= start_date", name="ck_employee_leaves_range"),
    )
    op.create_index("ix_leaves_employee", "employee_leaves", ["employee_id", "start_date"])

    op.create_table(
        "shift_segments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("end_at > start_at", name="ck_shift_segments_order"),
    )
    op.create_index("ix_shifts_employee_start", "shift_segments", ["employee_id", "start_at"])
    op.create_index("ix_shifts_store_start", "shift_segments", ["store_id", "start_at"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column("settled_by", sa.BigInteger(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["settled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "period_month", name="ux_payroll_runs_store_month"),
    )

    op.create_table(
        "payroll_lines",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("rate_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("ledger_entry_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["payroll_runs.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "employee_id", name="ux_payroll_lines_run_employee"),
        sa.CheckConstraint("hours >= 0", name="ck_payroll_lines_hours"),
        sa.CheckConstraint("amount >= 0", name="ck_payroll_lines_amount"),
    )


def downgrade() -> None:
    op.drop_table("payroll_lines")
    op.drop_table("payroll_runs")
    op.drop_index("ix_shifts_store_start", table_name="shift_segments")
    op.drop_index("ix_shifts_employee_start", table_name="shift_segments")
    op.drop_table("shift_segments")
    op.drop_index("ix_leaves_employee", table_name="employee_leaves")
    op.drop_table("employee_leaves")
    op.drop_index("ix_employees_store", table_name="employees")
    op.drop_table("employees")
