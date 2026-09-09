"""TD-T1 · T-PAY-01~05（testing.md §3，P0：T-PAY-02/03）。

[O-07 拍板 2026-09-09] 真实费率规则已落地（单价存员工档案）：
用例直接以 pay_type + unit_price 造数，不再依赖 DI 桩。
"""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.employees.models import Employee
from app.modules.ledger.models import LedgerEntry
from app.modules.payroll.models import PayrollRun
from tests.helpers import bearer


async def _setup(client, world, db_session, *, with_pay: bool = True) -> tuple[dict, str]:
    """S1 员工（默认 时薪 50）+ 本周一段 4h。返回 (employee, month)。"""
    h = bearer(world.m.token, world.s1_id)
    body: dict = {"name": "张三", "job_type": "long_term"}
    if with_pay:
        body |= {"pay_type": "hourly", "unit_price": "50"}
    r = await client.post("/employees", json=body, headers=h)
    assert r.status_code == 201, r.text
    emp = r.json()
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": emp["id"],
            "start_at": f"{monday.isoformat()}T10:00:00",
            "end_at": f"{monday.isoformat()}T14:00:00",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return emp, monday.strftime("%Y-%m")


async def test_t_pay_02_settle_posts_entry_matching_line(client, world, db_session):
    """P0 · AC-PAY-02/AC-REC-03：流水金额 == payroll_lines.amount；体带 amount → 422。"""
    emp, month = await _setup(client, world, db_session)
    assert emp["pay_type"] == "hourly" and Decimal(emp["unit_price"]) == Decimal("50")
    h = bearer(world.m.token, world.s1_id)

    # 请求体夹带金额字段 → 422 client_amount_forbidden（Locked）
    r = await client.post("/payroll/settle", json={"month": month, "amount": "999"}, headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "client_amount_forbidden"

    r = await client.post("/payroll/settle", json={"month": month}, headers=h)
    assert r.status_code == 201, r.text
    run = r.json()["run"]
    assert len(run["lines"]) == 1
    line = run["lines"][0]
    assert Decimal(line["amount"]) == Decimal("200.00")   # 4h × 50（真实费率规则）

    # 流水行：金额只读来自 payroll_line（filter=payroll 可查）
    r = await client.get("/ledger/entries?filter=payroll", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert Decimal(items[0]["amount"]) == Decimal(line["amount"])
    assert items[0]["source_type"] == "payroll"

    # 数据层：ledger_entries.amount 恒等 payroll_lines.amount
    entry = db_session.get(LedgerEntry, line["ledger_entry_id"])
    assert entry.amount == Decimal("200.00")
    assert entry.source_id is not None


async def test_t_pay_03_sm_settle_denied(client, world, db_session):
    """P0 · AC-PAY-03：店长结算 → 403 forbidden_role，零副作用。"""
    _emp, month = await _setup(client, world, db_session)
    r = await client.post(
        "/payroll/settle", json={"month": month},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"
    assert db_session.query(PayrollRun).filter_by(store_id=world.s1_id).count() == 0


async def test_t_pay_01_payroll_updates_on_shift_change(client, world, db_session):
    """AC-PAY-01：改班次 → GET /payroll 立即变（compute-on-read，无「计算」端点）。"""
    emp, month = await _setup(client, world, db_session)
    h = bearer(world.m.token, world.s1_id)

    r = await client.get(f"/payroll?month={month}", headers=h)
    assert Decimal(r.json()["total_hours"]) == Decimal("4.00")

    # 再加一段 2h → 立即 6h（无任何「计算」动作）
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": emp["id"],
            "start_at": f"{monday.isoformat()}T18:00:00",
            "end_at": f"{monday.isoformat()}T20:00:00",
        },
        headers=h,
    )
    assert r.status_code == 201
    r = await client.get(f"/payroll?month={month}", headers=h)
    assert Decimal(r.json()["total_hours"]) == Decimal("6.00")


async def test_t_pay_04_no_shifts_nothing_to_settle(client, world, db_session):
    """AC-PAY-04：无班次 → 422 nothing_to_settle，无分录凭空产生。"""
    r = await client.post(
        "/payroll/settle", json={"month": "2099-01"},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "nothing_to_settle"
    assert db_session.query(PayrollRun).filter_by(store_id=world.s1_id).count() == 0
    assert (
        db_session.query(LedgerEntry)
        .filter_by(store_id=world.s1_id, source_type="payroll")
        .count()
        == 0
    )


async def test_t_pay_05b_settle_body_with_amount_rejected(client, world, db_session):
    """AC-REC-03 / T-PAY-05b：settle 体夹带工资金额 → 422 client_amount_forbidden。"""
    for extra in ({"amount": "100"}, {"lines": []}, {"hours": "8"}, {"total_amount": "1"}):
        r = await client.post(
            "/payroll/settle", json={"month": "2099-01", **extra},
            headers=bearer(world.sm.token, world.s1_id),
        )
        assert r.status_code == 422, extra
        assert r.json()["detail"] == "client_amount_forbidden", extra


async def test_t_pay_rate_rule_missing(client, world, db_session):
    """[O-07]：员工未设置计薪方式/单价 → settle 422 rate_rule_missing。"""
    _emp, month = await _setup(client, world, db_session, with_pay=False)
    r = await client.post(
        "/payroll/settle", json={"month": month},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "rate_rule_missing"
