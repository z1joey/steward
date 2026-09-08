"""TC-T1 · T-DIV-01/02/03（testing.md §3，P0：T-DIV-01/02，AC-DIV-01/02/03）。

公账余额以 posting service 数据层造数（manual 分录不动公账，O-05）。
"""

from datetime import date
from decimal import Decimal

from app.core.deps import StoreContext
from app.enums import Direction, SourceType, TxnDirection
from app.modules.dividend.models import DividendRun
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount, Store
from app.modules.auth.models import User
from app.posting.service import EntryDraft, PublicTxnDraft, post
from tests.helpers import bearer


async def _seed_balance(db_session, world, amount: str) -> PublicAccount:
    """公账充值（数据层 post，in 方向）。返回公账行（balance + version）。"""
    user = db_session.get(User, world.m.user_id)
    store = db_session.get(Store, world.s1_id)
    ctx = StoreContext(user=user, store=store, membership=None, role=None)
    post(
        db_session,
        ctx,
        EntryDraft(
            entry_date=date(2026, 9, 1),
            amount=Decimal(amount),
            direction=Direction.income,
            memo="充值",
            source_type=SourceType.manual,
            source_id=None,
        ),
        PublicTxnDraft(direction=TxnDirection.inn, require_sufficient_balance=False),
    )
    db_session.commit()
    db_session.expire_all()
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal(amount)
    return acct


async def test_t_div_01_confirm_within_balance_posts_and_deducts(client, world, db_session):
    """P0 · AC-DIV-01：amount ≤ 余额 → entry + txn + 扣公账 + run 落库。"""
    acct = await _seed_balance(db_session, world, "500")
    r = await client.post(
        "/dividends/confirm",
        json={"amount": "200", "memo": "中秋分红", "public_account_version": acct.version},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    body = r.json()

    assert Decimal(body["public"]["balance"]) == Decimal("300")
    assert body["entry"]["source_type"] == "dividend"
    assert body["entry"]["direction"] == "expense"

    db_session.expire_all()
    entry_row = db_session.get(LedgerEntry, body["entry"]["id"])
    run = db_session.get(DividendRun, body["run"]["id"])
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("300")
    assert entry_row.source_id == run.id          # runs 落库后回填 source_id
    assert run.ledger_entry_id == entry_row.id
    assert run.public_txn_id is not None
    txn = db_session.get(PublicAccountTxn, run.public_txn_id)
    assert txn.direction == "out"
    assert txn.balance_after == Decimal("300")


async def test_t_div_02_confirm_over_balance_rejected_zero_side_effects(client, world, db_session):
    """P0 · AC-DIV-02：amount > 余额 → 422 insufficient_balance；无分录、余额不变。"""
    acct = await _seed_balance(db_session, world, "100")
    r = await client.post(
        "/dividends/confirm",
        json={"amount": "100.01", "public_account_version": acct.version},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == "insufficient_balance"

    db_session.expire_all()
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("100")            # 余额不变
    assert (
        db_session.query(LedgerEntry)
        .filter_by(store_id=world.s1_id, source_type="dividend")
        .count()
        == 0
    )                                                # 无分录
    assert db_session.query(DividendRun).filter_by(store_id=world.s1_id).count() == 0


async def test_t_div_03_sm_confirm_denied(client, world, db_session):
    """AC-DIV-03：店长确认发放 → 403（UI 只读无按钮见 TC-06/TF-04）。"""
    acct = await _seed_balance(db_session, world, "80")
    r = await client.post(
        "/dividends/confirm",
        json={"amount": "10", "public_account_version": acct.version},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"
    db_session.expire_all()
    acct = db_session.query(PublicAccount).filter_by(store_id=world.s1_id).one()
    assert acct.balance == Decimal("80")
