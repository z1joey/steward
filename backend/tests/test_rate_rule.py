"""O07-T · 费率规则用例（[O-07 拍板 2026-09-09]，AC-PAY-01/02/04 · AC-EMP-02）。

按小时：应发 = Σ段工时 × 时薪；按日：应发 = 自然日出勤天数 × 日薪
（当日多段计 1 天）；未设置计薪 → 预览 amount null、settle 422 rate_rule_missing；
结算后 payroll_lines.rate_snapshot 落算薪明细。
"""

from datetime import date
from decimal import Decimal

from app.modules.payroll.models import PayrollLine
from tests.helpers import bearer


async def _create_employee(client, world, body: dict) -> dict:
    r = await client.post(
        "/employees", json=body, headers=bearer(world.m.token, world.s1_id)
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _add_segment(
    client, world, employee_id: int, day: str, start: str, end: str
) -> None:
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": employee_id,
            "start_at": f"{date.today().isoformat()[:8]}{day}T{start}:00",
            "end_at": f"{date.today().isoformat()[:8]}{day}T{end}:00",
        },
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text


def _month() -> str:
    return date.today().strftime("%Y-%m")


async def test_hourly_multi_segment_sums(client, world, db_session):
    """按小时：同月多段工时求和 × 时薪；worked_days 仍如实统计。"""
    emp = await _create_employee(
        client, world, {"name": "张三", "job_type": "long_term",
                         "pay_type": "hourly", "unit_price": "50"}
    )
    await _add_segment(client, world, emp["id"], "10", "10:00", "14:00")   # 4h
    await _add_segment(client, world, emp["id"], "20", "18:00", "20:00")   # 2h
    month = _month()

    r = await client.get(f"/payroll?month={month}", headers=bearer(world.m.token, world.s1_id))
    assert r.status_code == 200
    row = r.json()["preview"][0]
    assert Decimal(row["hours"]) == Decimal("6.00")
    assert row["worked_days"] == 2
    assert row["pay_type"] == "hourly"
    assert Decimal(row["amount"]) == Decimal("300.00")   # 6h × 50
    assert Decimal(r.json()["total_amount"]) == Decimal("300.00")


async def test_daily_natural_days_counted_once(client, world, db_session):
    """按日：同日多段计 1 天；应发 = 出勤天数 × 日薪。"""
    emp = await _create_employee(
        client, world, {"name": "李四", "job_type": "temporary",
                         "pay_type": "daily", "unit_price": "150"}
    )
    await _add_segment(client, world, emp["id"], "10", "10:00", "12:00")   # 第 1 天
    await _add_segment(client, world, emp["id"], "10", "14:00", "18:00")   # 同日第二段 → 不重复计
    await _add_segment(client, world, emp["id"], "11", "09:00", "17:00")   # 第 2 天
    month = _month()

    r = await client.get(f"/payroll?month={month}", headers=bearer(world.m.token, world.s1_id))
    row = r.json()["preview"][0]
    assert row["worked_days"] == 2
    assert row["pay_type"] == "daily"
    assert Decimal(row["hours"]) == Decimal("14.00")
    assert Decimal(row["amount"]) == Decimal("300.00")   # 2 天 × 150（与工时无关）


async def test_no_pay_config_amount_null_and_settle_rejected(client, world, db_session):
    """未设置计薪 → 预览 amount null；settle → 422 rate_rule_missing。"""
    emp = await _create_employee(client, world, {"name": "王五", "job_type": "weekend"})
    await _add_segment(client, world, emp["id"], "10", "10:00", "14:00")
    month = _month()
    h = bearer(world.m.token, world.s1_id)

    r = await client.get(f"/payroll?month={month}", headers=h)
    row = r.json()["preview"][0]
    assert row["amount"] is None
    assert row["pay_type"] is None
    assert r.json()["total_amount"] is None

    r = await client.post("/payroll/settle", json={"month": month}, headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "rate_rule_missing"


async def test_put_pay_fields_versioned(client, world, db_session):
    """AC-EMP-02：PUT 配置/变更计薪字段带 version；旧 version → 409。"""
    emp = await _create_employee(client, world, {"name": "赵六", "job_type": "summer"})
    h = bearer(world.m.token, world.s1_id)

    # 只带一半字段 → 422（成对校验）
    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": emp["version"], "pay_type": "hourly"},
        headers=h,
    )
    assert r.status_code == 422

    # 单价 ≤ 0 → 422
    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": emp["version"], "pay_type": "hourly", "unit_price": "0"},
        headers=h,
    )
    assert r.status_code == 422

    # 正常配置
    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": emp["version"], "pay_type": "hourly", "unit_price": "40"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pay_type"] == "hourly"
    assert Decimal(body["unit_price"]) == Decimal("40.00")

    # 旧 version → 409
    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": emp["version"], "pay_type": "daily", "unit_price": "1"},
        headers=h,
    )
    assert r.status_code == 409

    # 改为按日
    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": body["version"], "pay_type": "daily", "unit_price": "120"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["pay_type"] == "daily"


async def test_settle_rate_snapshot_breakdown(client, world, db_session):
    """AC-PAY-02：结算后 payroll_lines.rate_snapshot 落算薪明细（hourly 与 daily）。"""
    month = _month()
    hourly = await _create_employee(
        client, world, {"name": "张三", "job_type": "long_term",
                         "pay_type": "hourly", "unit_price": "50"}
    )
    await _add_segment(client, world, hourly["id"], "10", "10:00", "14:00")
    daily = await _create_employee(
        client, world, {"name": "李四", "job_type": "temporary",
                         "pay_type": "daily", "unit_price": "150"}
    )
    await _add_segment(client, world, daily["id"], "10", "09:00", "17:00")

    r = await client.post(
        "/payroll/settle", json={"month": month}, headers=bearer(world.m.token, world.s1_id)
    )
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["run"]["total_amount"]) == Decimal("350.00")   # 200 + 150

    lines = db_session.query(PayrollLine).order_by(PayrollLine.id).all()
    by_amount = {str(l.amount): l for l in lines}
    hourly_snap = by_amount["200.00"].rate_snapshot
    daily_snap = by_amount["150.00"].rate_snapshot

    assert hourly_snap["pay_type"] == "hourly"
    assert Decimal(hourly_snap["unit_price"]) == Decimal("50")
    assert Decimal(hourly_snap["base_hours"]) == Decimal("4.00")
    assert hourly_snap["overtime"] is None and hourly_snap["bonus"] is None   # 扩展位
    assert daily_snap["pay_type"] == "daily"
    assert daily_snap["worked_days"] == 1


async def test_pay_type_change_reflects_immediately(client, world, db_session):
    """AC-PAY-01：改计薪方式 → GET /payroll 立即变（compute-on-read）。"""
    emp = await _create_employee(
        client, world, {"name": "张三", "job_type": "long_term",
                         "pay_type": "hourly", "unit_price": "50"}
    )
    await _add_segment(client, world, emp["id"], "10", "10:00", "14:00")   # 4h / 1 天
    month = _month()
    h = bearer(world.m.token, world.s1_id)

    r = await client.get(f"/payroll?month={month}", headers=h)
    assert Decimal(r.json()["preview"][0]["amount"]) == Decimal("200.00")

    r = await client.put(
        f"/employees/{emp['id']}",
        json={"version": emp["version"], "pay_type": "daily", "unit_price": "300"},
        headers=h,
    )
    assert r.status_code == 200
    r = await client.get(f"/payroll?month={month}", headers=h)
    assert Decimal(r.json()["preview"][0]["amount"]) == Decimal("300.00")   # 1 天 × 300
