"""TC-T1 · T-PAY-05a（recurring wages 手填 → 422）+ AC-REC-01（period≠month → 422）。

工资类周期禁止手填（Locked，AC-REC-03）；周期单位仅 month（Locked，AC-REC-01）。
"""

from tests.helpers import bearer


async def test_t_pay_05a_recurring_wages_hand_filled_amount_rejected(client, world):
    """T-PAY-05a · AC-REC-03：wages 带金额 / 固定位 一律 422 wages_not_hand_filled。"""
    h = bearer(world.m.token, world.s1_id)
    r = await client.post(
        "/ledger/recurring",
        json={"name": "员工工资", "kind": "wages", "is_fixed": False,
              "fixed_amount": "5000"},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "wages_not_hand_filled"

    r = await client.post(
        "/ledger/recurring",
        json={"name": "员工工资", "kind": "wages", "is_fixed": True},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "wages_not_hand_filled"


async def test_t_rec_01_period_must_be_month(client, world):
    """AC-REC-01：period 仅 month；传非 month → 422 period_must_be_month。"""
    r = await client.post(
        "/ledger/recurring",
        json={"name": "周租金", "kind": "rent", "is_fixed": True,
              "fixed_amount": "800", "period": "week"},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "period_must_be_month"


async def test_t_rec_occurrence_wages_denied_and_fixed_amount_used(client, world, db_session):
    """AC-REC-03：wages 项记本月一律 422；固定项记本月取 fixed_amount 忽略入参。"""
    from app.modules.recurring.models import RecurringExpense

    h = bearer(world.m.token, world.s1_id)
    # 建 wages 项（无金额合法）
    r = await client.post(
        "/ledger/recurring",
        json={"name": "员工工资", "kind": "wages", "is_fixed": False},
        headers=h,
    )
    assert r.status_code == 201, r.text
    wages = r.json()
    r = await client.post(
        f"/ledger/recurring/{wages['id']}/occurrences",
        json={"period_month": "2026-09", "amount": "999", "version": wages["version"]},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "wages_not_hand_filled"

    # 固定 rent 项：记本月忽略 amount，取 fixed_amount
    r = await client.post(
        "/ledger/recurring",
        json={"name": "房租", "kind": "rent", "is_fixed": True, "fixed_amount": "3000"},
        headers=h,
    )
    rent = r.json()
    r = await client.post(
        f"/ledger/recurring/{rent['id']}/occurrences",
        json={"period_month": "2026-09", "amount": "1", "version": rent["version"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["occurrence"]["amount"] == "3000.00"

    # 重复记本月 → 409（one-shot，UNIQUE 兜底）
    r = await client.post(
        f"/ledger/recurring/{rent['id']}/occurrences",
        json={"period_month": "2026-09", "version": rent["version"] + 1},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "period_already_recorded"
