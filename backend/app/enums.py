"""枚举字面量集中地 [C · O-03]。

存库 / JSON 用英文小写字面量；UI 中文文案见 frontend/src/shared/enums.ts。
拍板后在此一次性替换，再做一次迁移更新 CHECK 约束（B-specs §7）。
"""

from enum import Enum


class Role(str, Enum):
    manager = "manager"                    # 管理者
    store_manager = "store_manager"        # 店长


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class TransferStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"                  # 拒绝 / 取消 [Open O-08]


class ClaimStatus(str, Enum):
    pending = "pending"
    posted = "posted"
    rejected = "rejected"                  # [C · O-04]；无 approved-not-posted


class SourceType(str, Enum):
    manual = "manual"
    claim = "claim"
    payroll = "payroll"
    dividend = "dividend"
    recurring = "recurring"
    adjustment = "adjustment"              # 公账余额调整（管理者，原因必填）


class Direction(str, Enum):
    income = "income"
    expense = "expense"


class TxnDirection(str, Enum):
    inn = "in"
    out = "out"


class RecurringKind(str, Enum):
    rent = "rent"
    utilities = "utilities"
    wages = "wages"


class RecurringPeriod(str, Enum):
    month = "month"                        # Locked：仅 month


class JobType(str, Enum):
    long_term = "long_term"
    summer = "summer"
    winter = "winter"
    weekend = "weekend"
    temporary = "temporary"


class EmployeeStatus(str, Enum):
    active = "active"
    resigned = "resigned"                  # [C · O-13]；「请假」为展示态


# 店长 Deny 清单（api.md §5，Locked）。对应路由全部挂 require_role(manager)；
# 角色拒绝矩阵测试遍历该常量（testing.md §4）。
MANAGER_ONLY: frozenset[str] = frozenset(
    {
        "claims.approve",
        "claims.reject",
        "payroll.settle",
        "dividend.confirm",
        "ledger.reverse",
        "invites.create",
        "transfers.create",
    }
)
