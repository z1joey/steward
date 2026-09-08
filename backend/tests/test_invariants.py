"""TF-02 · 数据层断言（testing.md §1 数据层 / A-plan R4 / AC-LED-04/08 · AC-DIV-01）。

1. approve 事务故障注入：txn 插入失败 → entry 回滚、claim 仍 pending；
2. 冲正后原行全列不变（除 reversed_by_id / version）；
3. 并发 approve + dividend 后 public_accounts.balance == Σ txns(in − out)。
"""

import asyncio
import uuid
from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from app.core.db import get_db
from app.main import create_app
from app.modules.claims.models import ExpenseClaim
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import Ledger, PublicAccount, Store
from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.invites.models import Invite
from app.modules.transfers.models import Transfer
from tests.helpers import bearer, create_store, register_and_login, unique_phone


def _real_app(engine) -> tuple:
    factory = sessionmaker(bind=engine)
    app = create_app()

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app, factory


def _cleanup(factory, store_id: int, user_ids: list[int]) -> None:
    db = factory()
    try:
        from app.modules.dividend.models import DividendRun

        for model, col in (
            (DividendRun, DividendRun.store_id),
            (PublicAccountTxn, PublicAccountTxn.store_id),
            (ExpenseClaim, ExpenseClaim.store_id),
            (LedgerEntry, LedgerEntry.store_id),
            (Transfer, Transfer.store_id),
            (Invite, Invite.store_id),
            (Membership, Membership.store_id),
            (Ledger, Ledger.store_id),
            (PublicAccount, PublicAccount.store_id),
        ):
            db.query(model).filter(col == store_id).delete(synchronize_session=False)
        db.query(Store).filter(Store.id == store_id).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


async def _post_claim_and_get_id(client, world) -> int:
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-02", "amount": "30", "memo": "打车",
              "needs_reimbursement": True},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["claim"]["id"]


async def test_approve_txn_failure_rolls_back_entry_and_claim(engine, monkeypatch):
    """AC-LED-04 故障注入：公账流水插入失败 → 整体 ROLLBACK，claim 仍 pending。"""
    app, factory = _real_app(engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        tag = uuid.uuid4().hex[:8]
        m = await register_and_login(client, unique_phone(f"m-{tag}-"))
        sm = await register_and_login(client, unique_phone(f"sm-{tag}-"))
        store_id = await create_store(client, m, f"FI-{tag}")
        db = factory()
        try:
            db.add(Membership(user_id=sm.user_id, store_id=store_id, role="store_manager", version=1))
            db.commit()
            db.close()

            r = await client.post(
                "/ledger/entries",
                json={"date": "2026-09-02", "amount": "30", "memo": "打车",
                      "needs_reimbursement": True},
                headers=bearer(sm.token, store_id),
            )
            claim_id = r.json()["claim"]["id"]

            # 故障注入：txn 模型构造即抛（仅测试）
            class _Boom(Exception):
                pass

            real_txn = PublicAccountTxn

            def _broken_txn(*args, **kwargs):
                raise _Boom("txn insert failure")

            monkeypatch.setattr(
                "app.posting.service.PublicAccountTxn",
                _broken_txn,
            )
            # 非受控异常穿透 ASGI 层 → 客户端侧直接抛出；事务已 ROLLBACK
            with pytest.raises(_Boom):
                await client.post(
                    f"/claims/{claim_id}/approve",
                    json={"version": 1},
                    headers=bearer(m.token, store_id),
                )
            monkeypatch.undo()

            # 数据层（真实提交会话）：claim 仍 pending、无分录、无流水、余额 0
            db = factory()
            try:
                assert db.get(ExpenseClaim, claim_id).status == "pending"
                assert (
                    db.query(LedgerEntry).filter_by(store_id=store_id).count() == 0
                )
                assert (
                    db.query(real_txn).filter_by(store_id=store_id).count() == 0
                )
                acct = db.query(PublicAccount).filter_by(store_id=store_id).one()
                assert acct.balance == Decimal("0")
            finally:
                db.close()
        finally:
            _cleanup(factory, store_id, [m.user_id, sm.user_id])


async def test_reverse_leaves_original_columns_intact(client, world, db_session):
    """AC-LED-08：冲正后原行除 reversed_by_id / version 外全列不变。"""
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-02", "amount": "30", "memo": "打车",
              "needs_reimbursement": True},
        headers=bearer(world.sm.token, world.s1_id),
    )
    claim_id = r.json()["claim"]["id"]
    r = await client.post(
        f"/claims/{claim_id}/approve", json={"version": 1},
        headers=bearer(world.m.token, world.s1_id),
    )
    entry_id = r.json()["entry"]["id"]

    db_session.expire_all()
    before = {
        c.name: getattr(db_session.get(LedgerEntry, entry_id), c.name)
        for c in LedgerEntry.__table__.columns
    }

    r = await client.post(
        f"/ledger/entries/{entry_id}/reverse", json={"version": before["version"]},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    reversal_id = r.json()["entry"]["id"]

    db_session.expire_all()
    after = {
        c.name: getattr(db_session.get(LedgerEntry, entry_id), c.name)
        for c in LedgerEntry.__table__.columns
    }
    changed = {k for k in before if before[k] != after[k]}
    assert changed == {"reversed_by_id", "version"}
    assert after["reversed_by_id"] == reversal_id
    assert after["version"] == before["version"] + 1


async def test_balance_equals_txn_sum_after_concurrent_approve_and_dividend(engine):
    """A-plan R4 / AC-DIV-01：并发 approve + dividend 后 balance == Σ txns(in−out)。"""
    from app.modules.dividend.models import DividendRun

    app, factory = _real_app(engine)
    clients = [
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
        for _ in range(3)
    ]
    tag = uuid.uuid4().hex[:8]
    m = await register_and_login(clients[0], unique_phone(f"m-{tag}-"))
    sm = await register_and_login(clients[0], unique_phone(f"sm-{tag}-"))
    store_id = await create_store(clients[0], m, f"INV-{tag}")
    try:
        db = factory()
        db.add(Membership(user_id=sm.user_id, store_id=store_id, role="store_manager", version=1))
        db.commit()
        db.close()

        # 公账充值 500（数据层 post in）
        from app.core.deps import StoreContext
        from app.enums import Direction, SourceType, TxnDirection
        from app.posting.service import EntryDraft, PublicTxnDraft, post

        db = factory()
        user = db.get(User, m.user_id)
        store = db.get(Store, store_id)
        ctx = StoreContext(user=user, store=store, membership=None, role=None)
        post(
            db, ctx,
            EntryDraft(entry_date=date(2026, 9, 1), amount=Decimal("500"),
                       direction=Direction.income, memo="充值",
                       source_type=SourceType.manual, source_id=None),
            PublicTxnDraft(direction=TxnDirection.inn, require_sufficient_balance=False),
        )
        db.commit()
        db.close()

        # pending 报销 100
        r = await clients[0].post(
            "/ledger/entries",
            json={"date": "2026-09-02", "amount": "100", "memo": "报销",
                  "needs_reimbursement": True},
            headers=bearer(sm.token, store_id),
        )
        claim_id = r.json()["claim"]["id"]
        acct = factory().query(PublicAccount).filter_by(store_id=store_id).one()
        acct_version = acct.version

        # 并发：approve（out 100）与 dividend（out 200）
        results = await asyncio.gather(
            clients[0].post(
                f"/claims/{claim_id}/approve", json={"version": 1},
                headers=bearer(m.token, store_id),
            ),
            clients[1].post(
                "/dividends/confirm",
                json={"amount": "200", "memo": "分红", "public_account_version": acct_version},
                headers=bearer(m.token, store_id),
            ),
        )
        assert all(r.status_code in (200, 201) for r in results), [
            (r.status_code, r.text) for r in results
        ]

        db = factory()
        try:
            acct = db.query(PublicAccount).filter_by(store_id=store_id).one()
            txns = db.query(PublicAccountTxn).filter_by(store_id=store_id).all()
            net = sum(
                (t.amount if t.direction == "in" else -t.amount for t in txns),
                Decimal("0"),
            )
            assert len(txns) == 3            # 充值 + approve + dividend
            assert net == Decimal("500") - Decimal("100") - Decimal("200")
            assert acct.balance == net       # Locked 不变式（A-plan R4）
            assert db.query(DividendRun).filter_by(store_id=store_id).count() == 1
        finally:
            db.close()
    finally:
        for c in clients:
            await c.aclose()
        _cleanup(factory, store_id, [m.user_id, sm.user_id])
