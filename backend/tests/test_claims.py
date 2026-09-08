"""TB-T1 · T-CL-02 / T-CL-03（testing.md §3，P0，AC-LED-03/04）。

T-CL-02：勾「需要报销」→ expense_claims.status=pending，公账余额不变（Locked）。
T-CL-03：管理者「报销」→ 同一事务 entry + public_account_txn(out) + 扣余额；
claim → posted 且回填 ledger_entry_id。
"""

from decimal import Decimal

from app.enums import Direction, SourceType
from app.modules.claims.models import ExpenseClaim
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount
from app.posting.service import EntryDraft, post
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


async def test_t_cl_01_manual_entry_direct(client, world, db_session):
    """TB-T2 · AC-LED-01/02：不勾报销 → 直接产生可查流水分录（不断言公账，O-05）。"""
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-01", "amount": "12.5", "memo": "买耗材",
              "needs_reimbursement": False},
        headers=bearer(world.sm.token, world.s1_id),   # 店长也可记一笔（§2.5）
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "entry"
    assert body["entry"]["source_type"] == "manual"
    assert body["entry"]["direction"] == "expense"     # O-23 默认 expense

    r = await client.get("/ledger/entries?filter=manual", headers=bearer(world.m.token, world.s1_id))
    assert r.status_code == 200
    assert [i["id"] for i in r.json()["items"]] == [body["entry"]["id"]]


async def test_t_cl_04_reject_no_entry_no_deduction(client, world, db_session):
    """TB-T2 · AC-LED-05：驳回 → 不入账不扣公账；status=rejected（O-04）且不进流水。"""
    claim = (await _create_claim(client, world))["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/reject",
        json={"version": claim["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["claim"]["status"] == "rejected"

    db_session.expire_all()
    assert db_session.query(LedgerEntry).filter_by(store_id=world.s1_id).count() == 0
    assert db_session.query(PublicAccountTxn).filter_by(store_id=world.s1_id).count() == 0
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("0")
    # rejected 不出现在流水（O-04）：filter=claim 无行
    r = await client.get("/ledger/entries?filter=claim", headers=bearer(world.m.token, world.s1_id))
    assert r.json()["items"] == []


async def test_t_cl_05_sm_approve_reject_denied(client, world, db_session):
    """TB-T2 · AC-LED-06：店长 approve/reject API 拒绝（UI 隐藏见 e2e，TF-04）。"""
    claim = (await _create_claim(client, world))["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/approve", json={"version": claim["version"]},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403 and r.json()["detail"] == "forbidden_role"
    r = await client.post(
        f"/claims/{claim['id']}/reject", json={"version": claim["version"]},
        headers=bearer(world.sm2.token, world.s1_id),
    )
    assert r.status_code == 403 and r.json()["detail"] == "forbidden_role"
    # 零副作用
    db_session.expire_all()
    assert db_session.get(ExpenseClaim, claim["id"]).status == "pending"
    assert db_session.query(PublicAccountTxn).filter_by(store_id=world.s1_id).count() == 0


async def test_t_cl_06_filter_six_values(client, world, db_session):
    """TB-T2 · AC-LED-07：全部/手工/报销/工资/分红/周期 六值过滤正确。

    payroll / dividend / recurring 分录尚未有产生管道（Phase C/D），
    以数据层直插代表行，验证 filter 路由正确性。
    """
    from datetime import date

    from app.modules.auth.models import User
    from app.modules.stores.models import Ledger, Store

    # manual + claim（posted）经 API 产生
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-01", "amount": "10", "memo": "手工",
              "needs_reimbursement": False},
        headers=bearer(world.m.token, world.s1_id),
    )
    manual_id = r.json()["entry"]["id"]
    claim = (await _create_claim(client, world))["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/approve", json={"version": claim["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    posted_claim_entry_id = r.json()["entry"]["id"]

    # 直插 payroll / dividend / recurring 分录
    ledger = db_session.query(Ledger).filter_by(store_id=world.s1_id).one()
    user = db_session.get(User, world.m.user_id)
    store = db_session.get(Store, world.s1_id)
    from app.core.deps import StoreContext

    ctx = StoreContext(user=user, store=store, membership=None, role=None)
    seeded = {}
    for st in ("payroll", "dividend", "recurring"):
        result = post(
            db_session, ctx,
            EntryDraft(entry_date=date(2026, 9, 5), amount=Decimal("7"),
                       direction=Direction.expense, memo=f"seed-{st}",
                       source_type=SourceType(st), source_id=None),
            None,
        )
        seeded[st] = result.entry_id
    db_session.flush()

    async def ids_for(filter_value: str) -> list[int]:
        r = await client.get(
            f"/ledger/entries?filter={filter_value}",
            headers=bearer(world.m.token, world.s1_id),
        )
        assert r.status_code == 200
        return [i["id"] for i in r.json()["items"]]

    assert await ids_for("manual") == [manual_id]
    assert await ids_for("claim") == [posted_claim_entry_id]
    assert await ids_for("payroll") == [seeded["payroll"]]
    assert await ids_for("dividend") == [seeded["dividend"]]
    assert await ids_for("recurring") == [seeded["recurring"]]
    all_ids = set(await ids_for("all"))
    assert all_ids == {manual_id, posted_claim_entry_id, *seeded.values()}


async def test_t_iso_02_ledger_isolation_between_stores(client, world, db_session):
    """TB-T2 · AC-ISO-02：S1/S2 流水不串（同用户两店，切 X-Store-Id 仅见本店）。"""
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-01", "amount": "11", "memo": "S1支出",
              "needs_reimbursement": False},
        headers=bearer(world.m.token, world.s1_id),
    )
    s1_entry_id = r.json()["entry"]["id"]
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-01", "amount": "22", "memo": "S2支出",
              "needs_reimbursement": False},
        headers=bearer(world.m.token, world.s2_id),
    )
    s2_entry_id = r.json()["entry"]["id"]

    r = await client.get("/ledger/entries", headers=bearer(world.m.token, world.s1_id))
    assert [i["id"] for i in r.json()["items"]] == [s1_entry_id]
    r = await client.get("/ledger/entries", headers=bearer(world.m.token, world.s2_id))
    assert [i["id"] for i in r.json()["items"]] == [s2_entry_id]

    # 跨店 claim 操作 → 404
    claim = (await _create_claim(client, world))["claim"]
    r = await client.post(
        f"/claims/{claim['id']}/approve", json={"version": claim["version"]},
        headers=bearer(world.m.token, world.s2_id),
    )
    assert r.status_code == 404
