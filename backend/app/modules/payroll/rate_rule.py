"""费率规则（B-specs §4.2 · [O-07] 拍板 2026-09-09）。

拍板结论：单价存员工档案（unit_price），计薪方式员工自选（hourly / daily）；
按日口径 = 自然日出勤（当日有班段记 1 天，同日多段不重复）。
算法按工种表驱动（JOB_ALGORITHM 扩展位），未命中工种时用员工档案的 pay_type。

加班费 / 奖金等额外人力支出本期不启用（见 README TODO）；
snapshot 预留 overtime / bonus 扩展位，结算时整体落入
payroll_lines.rate_snapshot（AC-PAY-02 审计依据）。

pay_type / unit_price 缺失 → None → GET /payroll 应发 null（UI「未设置计薪」），
settle → 422 rate_rule_missing。测试可 monkeypatch 本函数作 DI 桩
（keyword 默认参数保证旧签名 (e, hours, month) 兼容）。
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# —— 加班规则（占位常量，本期不启用）——
OVERTIME_THRESHOLD_HOURS = Decimal("8")
OVERTIME_MULTIPLIER = Decimal("1.5")

# 按工种固定算法的扩展位：job_type -> "hourly" | "daily"；
# 未配置的工种沿用员工档案 pay_type（拍板口径：员工自选）。
JOB_ALGORITHM: dict[str, str] = {}

_CENTS = Decimal("0.01")


@dataclass
class RateOutcome:
    """单次算薪结果：应发金额 + 落 payroll_lines.rate_snapshot 的明细。"""

    amount: Decimal
    snapshot: dict[str, Any] = field(default_factory=dict)


def compute(
    employee: Any,
    hours: Decimal,
    month: str,
    worked_days: int = 0,
) -> RateOutcome | None:
    """rate_rule(employee, hours, month[, worked_days]) → 应发或 None（不可得）。

    worked_days：当月自然日出勤天数（仅 daily 算法使用）。
    """
    job_algorithm = JOB_ALGORITHM.get(getattr(employee, "job_type", None))
    pay_type = job_algorithm or getattr(employee, "pay_type", None)
    unit_price = getattr(employee, "unit_price", None)
    if pay_type not in ("hourly", "daily") or unit_price is None:
        return None

    if pay_type == "hourly":
        amount = (hours * unit_price).quantize(_CENTS)
        snapshot: dict[str, Any] = {
            "pay_type": pay_type,
            "unit_price": str(unit_price),
            "base_hours": str(hours.quantize(_CENTS)),
            "amount": str(amount),
        }
    else:
        amount = (Decimal(worked_days) * unit_price).quantize(_CENTS)
        snapshot = {
            "pay_type": pay_type,
            "unit_price": str(unit_price),
            "worked_days": worked_days,
            "amount": str(amount),
        }
    # 额外人力支出扩展位（加班费 / 奖金，README TODO）：结算明细按项追加
    snapshot["overtime"] = None
    snapshot["bonus"] = None
    return RateOutcome(amount=amount, snapshot=snapshot)
