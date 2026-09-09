"""公账余额调整用例（管理者受控盘点纠错；posting 管道约束 + 原因必填）。"""

from decimal import Decimal

from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount as PA
from tests.helpers import bearer


def _balance(db_session, store_id: int) -> Decimal:
    return db_session.query(PA).filter_by(store_id=store_id).one().balance


async def test_adjust_up_and_down_posts_paired_txn(client, world, db_session):
    """上调 0→500（income/in）再下调 500→300（expense/out）；原因入 memo；余额精确到位。"""
    h = bearer(world.m.token, world.s1_id)
    r = await client.get("/ledger/stats", headers=h)
    version = r.json()["public"]["version"]

    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "500", "reason": "盘点补录期初现金", "public_account_version": version},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["balance"]) == Decimal("500.00")
    assert Decimal(body["public_txn"]["balance_after"]) == Decimal("500.00")
    assert body["entry"]["direction"] == "income"
    assert Decimal(body["entry"]["amount"]) == Decimal("500.00")
    assert "盘点补录期初现金" in body["entry"]["memo"]
    assert body["entry"]["memo"].startswith("公账调整：")

    # 下调：用响应/刷新后的最新 version
    r = await client.get("/ledger/stats", headers=h)
    version = r.json()["public"]["version"]
    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "300", "reason": "冲正错账后核对", "public_account_version": version},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["balance"]) == Decimal("300.00")
    assert body["entry"]["direction"] == "expense"
    assert Decimal(body["entry"]["amount"]) == Decimal("200.00")
    assert Decimal(body["public_txn"]["balance_after"]) == Decimal("300.00")

    # 数据层：entry + txn 配对、余额一致（posting 管道唯一写入方）
    entry = db_session.get(LedgerEntry, body["entry"]["id"])
    txn = db_session.get(PublicAccountTxn, body["public_txn"]["id"])
    assert txn.ledger_entry_id == entry.id
    assert _balance(db_session, world.s1_id) == Decimal("300.00")


async def test_adjust_reason_required(client, world, db_session):
    """原因必填：缺失或空串 → 422（审计要求）。"""
    h = bearer(world.m.token, world.s1_id)
    r = await client.get("/ledger/stats", headers=h)
    version = r.json()["public"]["version"]

    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "100", "public_account_version": version},
        headers=h,
    )
    assert r.status_code == 422

    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "100", "reason": "   ", "public_account_version": version},
        headers=h,
    )
    assert r.status_code == 422
    assert _balance(db_session, world.s1_id) == Decimal("0")


async def test_adjust_stale_version_conflict(client, world, db_session):
    """乐观锁：version 过期 → 409 version_conflict，零副作用。"""
    h = bearer(world.m.token, world.s1_id)
    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "100", "reason": "旧版本", "public_account_version": 99},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "version_conflict"
    assert _balance(db_session, world.s1_id) == Decimal("0")


async def test_adjust_same_balance_no_change(client, world, db_session):
    """新余额等于当前余额 → 422 no_change，不产生分录。"""
    h = bearer(world.m.token, world.s1_id)
    r = await client.get("/ledger/stats", headers=h)
    version = r.json()["public"]["version"]
    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "0", "reason": "无变化", "public_account_version": version},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "no_change"
    assert (
        db_session.query(LedgerEntry).filter_by(store_id=world.s1_id).count() == 0
    )


async def test_adjust_sm_denied(client, world, db_session):
    """店长调整 → 403 forbidden_role，零副作用。"""
    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "100", "reason": "越权", "public_account_version": 1},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"
    assert _balance(db_session, world.s1_id) == Decimal("0")


async def test_adjust_isolation_between_stores(client, world, db_session):
    """店隔离：S2 的调整不影响 S1。"""
    h1 = bearer(world.m.token, world.s1_id)
    h2 = bearer(world.m.token, world.s2_id)
    r = await client.get("/ledger/stats", headers=h2)
    version = r.json()["public"]["version"]
    r = await client.post(
        "/public-account/adjust",
        json={"new_balance": "88", "reason": "S2 期初", "public_account_version": version},
        headers=h2,
    )
    assert r.status_code == 201
    assert _balance(db_session, world.s2_id) == Decimal("88.00")
    assert _balance(db_session, world.s1_id) == Decimal("0")
    assert db_session.query(PA).filter_by(store_id=world.s1_id).one().version == 1
