"""O07-1: employees 计薪字段 pay_type / unit_price（[O-07] 拍板 2026-09-09）

单价存员工档案：pay_type ∈ ('hourly','daily')，unit_price > 0，两者同空或同设。

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("pay_type", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_employees_pay_type",
        "employees",
        "pay_type IN ('hourly','daily')",
    )
    op.create_check_constraint(
        "ck_employees_unit_price",
        "employees",
        "unit_price IS NULL OR unit_price > 0",
    )
    op.create_check_constraint(
        "ck_employees_pay_pair",
        "employees",
        "(pay_type IS NULL) = (unit_price IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_employees_pay_pair", "employees", type_="check")
    op.drop_constraint("ck_employees_unit_price", "employees", type_="check")
    op.drop_constraint("ck_employees_pay_type", "employees", type_="check")
    op.drop_column("employees", "unit_price")
    op.drop_column("employees", "pay_type")
