"""利润率计算（B-specs §3.2）。

公式 [Open O-01]：拍板前返回 null，UI 显「—」；拍板后本函数单点替换。
"""

from decimal import Decimal


def compute(income: Decimal, expense: Decimal) -> float | None:
    return None
