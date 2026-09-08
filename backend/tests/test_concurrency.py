"""TA-T3 · T-TR-02 双会话并发 + T-CON-01 乐观锁（testing.md §3）。

rollback 夹具共享单连接（savepoint），产生不了两个真实事务；
双会话案改用独立 app 实例 + 真实 sessionmaker（真实 commit），
两台 httpx 会话 asyncio.gather 并发接受同一转让 → 恰一方 200。
数据真实落库，finally 按外键序清理。
"""

import asyncio
import uuid

import httpx
from sqlalchemy.orm import sessionmaker

from app.core.db import get_db
from app.main import create_app
from app.modules.auth.models import User
from app.modules.invites.models import Invite
from app.modules.memberships.models import Membership
from app.modules.stores.models import Ledger, PublicAccount, Store
from app.modules.transfers.models import Transfer
from tests.helpers import bearer, create_store, register_and_login, unique_phone


def _real_app(engine) -> tuple:
    """get_db → 真实提交 sessionmaker（区别于 conftest 的 savepoint 覆盖）。"""
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
        for model, col in (
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


async def test_t_tr_02_dual_session_concurrent_accept_one_wins(engine):
    """AC-TR-02 并发案：双会话同时接受同一转让 → 恰一方 200；恰 1 管理者。"""
    app, factory = _real_app(engine)
    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c1,
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c2,
    ):
        tag = uuid.uuid4().hex[:8]
        m = await register_and_login(c1, unique_phone(f"m-{tag}-"))
        t = await register_and_login(c1, unique_phone(f"t-{tag}-"))
        store_id = await create_store(c1, m, f"CONC-{tag}")
        r = await c1.post(
            f"/stores/{store_id}/transfers",
            json={"phone": t.phone},
            headers=bearer(m.token, store_id),
        )
        assert r.status_code == 201, r.text
        transfer_id = r.json()["id"]

        try:
            r1, r2 = await asyncio.gather(
                c1.post(
                    f"/transfers/{transfer_id}/accept",
                    json={"version": 1},
                    headers=bearer(t.token),
                ),
                c2.post(
                    f"/transfers/{transfer_id}/accept",
                    json={"version": 1},
                    headers=bearer(t.token),
                ),
            )
            assert sorted([r1.status_code, r2.status_code]) == [200, 409], (r1.text, r2.text)
            loser = r2 if r1.status_code == 200 else r1
            assert loser.json()["detail"] == "already_processed"

            db = factory()
            try:
                roles = dict(
                    db.query(Membership.user_id, Membership.role)
                    .filter(Membership.store_id == store_id)
                    .all()
                )
                assert roles[t.user_id] == "manager"
                assert roles[m.user_id] == "store_manager"   # 原管理者降店长
                managers = [uid for uid, role in roles.items() if role == "manager"]
                assert managers == [t.user_id]               # 恰 1 管理者
                assert db.get(Transfer, transfer_id).status == "accepted"
            finally:
                db.close()
        finally:
            _cleanup(factory, store_id, [m.user_id, t.user_id])


async def test_t_con_01_invite_accept_stale_version(client, world, db_session):
    """AC-CON-01（本分支映射）：旧 version 接受邀请 → 409 version_conflict，零副作用。"""
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    invite_id = r.json()["id"]

    r = await client.post(
        f"/invites/{invite_id}/accept",
        json={"version": 99},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "version_conflict"

    db_session.expire_all()
    # 零副作用：未产生 membership；邀请仍 pending；正确 version 仍可接受
    assert (
        db_session.query(Membership)
        .filter_by(store_id=world.s1_id, user_id=world.m2.user_id)
        .count()
        == 0
    )
    r = await client.get("/invites", headers=bearer(world.m2.token))
    assert any(i["id"] == invite_id for i in r.json()["invites"])
    r = await client.post(
        f"/invites/{invite_id}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 200, r.text


async def test_t_con_01_transfer_accept_stale_version(client, world, db_session):
    """AC-CON-01（本分支映射）：旧 version 接受转让 → 409 version_conflict，席位不变。"""
    r = await client.post(
        f"/stores/{world.s1_id}/transfers",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    transfer_id = r.json()["id"]

    r = await client.post(
        f"/transfers/{transfer_id}/accept",
        json={"version": 99},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "version_conflict"

    db_session.expire_all()
    managers = (
        db_session.query(Membership)
        .filter_by(store_id=world.s1_id, role="manager")
        .all()
    )
    assert [row.user_id for row in managers] == [world.m.user_id]   # 席位不变
    assert db_session.get(Transfer, transfer_id).status == "pending"
