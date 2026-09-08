"""TB-T1 · T-CL-02 / T-CL-03（testing.md §3，P0，AC-LED-03/04）。

T-CL-02：勾「需要报销」→ expense_claims.status=pending，公账余额不变（Locked）。
T-CL-03：管理者「报销」→ 同一事务 entry + public_account_txn(out) + 扣余额；
claim → posted 且回填 ledger_entry_id。
"""

from decimal import Decimal

from app.modules.claims.models import ExpenseClaim
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount
from tests.helpers import bearer


async def _create_claim(client, world, amount="30", memo="打车") -> dict:
    r = await client.post(
        "/ledger/entries",
        json={
            "date": "2026-09-02",
            "amount": amount,
            "memo": memo,
            "needs_reimbursement": True,
        },
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_t_cl_02_claim_pending_balance_untouched(client, world, db_session):
    """P0 · AC-LED-03：勾报销 → pending；公账余额不变、无分录产生。"""
    body = await _create_claim(client, world)
    assert body["kind"] == "claim"
    claim = body["claim"]
    assert claim["status"] == "pending"
    assert claim["requested_by"]["id"] == world.sm.user_id

    db_session.expire_all()
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("0")            # 公账不变（Locked）
    assert (
        db_session.query(LedgerEntry).filter_by(store_id=world.s1_id).count() == 0
    )                                              # 不触公账 = 无分录
    row = db_session.get(ExpenseClaim, claim["id"])
    assert row.status == "pending"


async def test_t_cl_03_approve_posts_entry_txn_balance_atomically(client, world, db_session):
    """P0 · AC-LED-04：approve 后 entry + txn + 余额同事务一致；claim posted。"""
    claim = (await _create_claim(client, world))["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/approve",
        json={"version": claim["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    entry, txn = body["entry"], body["public_txn"]

    assert body["claim"]["status"] == "posted"
    assert body["claim"]["ledger_entry_id"] == entry["id"]
    assert entry["source_type"] == "claim"
    assert entry["direction"] == "expense"
    assert txn["balance_after"] == "-30.00"

    db_session.expire_all()
    # 同事务一致性（testing.md §1 数据层）：entry / txn / 余额 / claim 四方对齐
    entry_row = db_session.get(LedgerEntry, entry["id"])
    txn_row = db_session.get(PublicAccountTxn, txn["id"])
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    claim_row = db_session.get(ExpenseClaim, claim["id"])
    assert entry_row.source_id == claim["id"]
    assert txn_row.ledger_entry_id == entry_row.id
    assert txn_row.direction == "out"
    assert txn_row.balance_after == acct.balance == Decimal("-30.00")
    assert acct.version == 2                       # 公账 version 随扣减推进
    assert claim_row.ledger_entry_id == entry_row.id
    assert claim_row.status == "posted"
