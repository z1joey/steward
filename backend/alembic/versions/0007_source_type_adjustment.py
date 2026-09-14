"""ADJ-2: source_type 增加 'adjustment'（公账余额调整公示/筛选）

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_ledger_entries_source_type", "ledger_entries", type_="check"
    )
    op.create_check_constraint(
        "ck_ledger_entries_source_type",
        "ledger_entries",
        "source_type IN ('manual','claim','payroll','dividend','recurring','adjustment')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ledger_entries_source_type", "ledger_entries", type_="check"
    )
    op.create_check_constraint(
        "ck_ledger_entries_source_type",
        "ledger_entries",
        "source_type IN ('manual','claim','payroll','dividend','recurring')",
    )
