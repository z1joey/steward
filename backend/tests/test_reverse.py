"""TB-T2 · T-REV-01 / T-REV-02（testing.md §3，AC-LED-08）。

T-REV-01：冲正 → 新反向分录 + 配对公账流水；原行字节级不变（仅 reversed_by_id/version）；
被冲正行再冲正 → 409。
T-REV-02：店长冲正 → 拒绝（UI 隐藏见 TF-04）。
"""

from decimal import Decimal

from app.modules.claims.models import ExpenseClaim
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount
from tests.helpers import bearer


async def _post_claim_entry(client, world) -> tuple[dict, int]:
    """勾报销 → approve → (approve 响应, entry_id)。"""
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-02", "amount": "30", "memo": "打车",
              "needs_reimbursement": True},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    claim = r.json()["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/approve",
        json={"version": claim["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 200, r.text
    return r.json(), r.json()["entry"]["id"]


async def test_t_rev_01_reverse_pairs_and_original_intact(client, world, db_session):
    """AC-LED-08：反向 + 配对；原行内容不变；再冲正 409；反向行再冲正 422。"""
    approved, entry_id = await _post_claim_entry(client, world)
    original_before = approved["entry"]

    r = await client.post(
        f"/ledger/entries/{entry_id}/reverse",
        json={"version": original_before["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    reversal, original = body["entry"], body["original"]

    # 反向行：金额相同、方向相反、冲正标记、配对公账 in
    assert reversal["is_reversal"] is True
    assert Decimal(reversal["amount"]) == Decimal(original_before["amount"])
    assert reversal["direction"] == "income"      # 原 expense
    assert body["public_txn"]["balance_after"] == "0.00"

    db_session.expire_all()
    # 原行字节级不变（amount/memo/date/source/direction），仅 reversed_by_id 回填
    row = db_session.get(LedgerEntry, entry_id)
    assert row.amount == Decimal("30")
    assert row.memo == "打车"
    assert row.direction == "expense"
    assert row.source_type == "claim"
    assert row.source_id == db_session.get(ExpenseClaim, approved["claim"]["id"]).id
    assert row.reversed_by_id == reversal["id"]
    assert row.version == original_before["version"] + 1

    # 被冲正的 claim 状态保持 posted [C]
    assert db_session.get(ExpenseClaim, approved["claim"]["id"]).status == "posted"

    # 公账：-30 → 0，两笔流水
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("0")
    txns = (
        db_session.query(PublicAccountTxn)
        .filter_by(store_id=world.s1_id)
        .order_by(PublicAccountTxn.id)
        .all()
    )
    assert [t.direction for t in txns] == ["out", "in"]

    # 原行再冲正 → 409 already_reversed
    r = await client.post(
        f"/ledger/entries/{entry_id}/reverse",
        json={"version": row.version},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "already_reversed"

    # 反向行本身不可再冲正 → 422 cannot_reverse_reversal [C]
    r = await client.post(
        f"/ledger/entries/{reversal['id']}/reverse",
        json={"version": reversal["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "cannot_reverse_reversal"


async def test_t_rev_02_sm_reverse_denied(client, world, db_session):
    """AC-LED-08：店长冲正 API 拒绝（403 forbidden_role），零副作用。"""
    _, entry_id = await _post_claim_entry(client, world)
    r = await client.post(
        f"/ledger/entries/{entry_id}/reverse",
        json={"version": 1},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"

    db_session.expire_all()
    row = db_session.get(LedgerEntry, entry_id)
    assert row.reversed_by_id is None and row.version == 1
    assert (
        db_session.query(PublicAccountTxn).filter_by(store_id=world.s1_id).count() == 1
    )
