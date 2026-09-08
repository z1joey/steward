"""费率规则接口（B-specs §4.2，[Open O-07]）。

拍板前返回 None → GET /payroll 应发为 null（UI「待费率拍板」），
settle 返回 422 rate_rule_missing。
拍板后在本地实现 compute；测试以 monkeypatch 本函数作依赖注入桩（仅测试，非产品功能）。
"""

from decimal import Decimal
from typing import Any


def compute(employee: Any, hours: Decimal, month: str) -> Decimal | None:
    """rate_rule(employee, hours, month) → 每员工应发金额或 None（不可得）。"""
    return None
