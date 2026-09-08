"""TA-T1（P0）· T-TR-01/02 + T-TR-03（AC-TR-01/02/03）。

席位（Locked）：一店恰 1 管理者；店长不限；未接受不变席。
"""

from sqlalchemy.orm import Session

from app.modules.memberships.models import Membership
from app.modules.transfers.models import Transfer
from tests.helpers import bearer


def _role_map(db: Session, store_id: int) -> dict[int, str]:
    rows = db.query(Membership).filter(Membership.store_id == store_id).all()
    return {row.user_id: row.role for row in rows}


def _manager_ids(db: Session, store_id: int) -> set[int]:
    rows = (
        db.query(Membership)
        .filter(Membership.store_id == store_id, Membership.role == "manager")
        .all()
    )
    return {row.user_id for row in rows}


async def _create_transfer(client, world, target) -> dict:
    r = await client.post(
        f"/stores/{world.s1_id}/transfers",
        json={"phone": target.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_t_tr_01_external_target_existing_managers_unaffected(
    client, world, db_session: Session
):
    """AC-TR-01 成功案（店外用户）：新人=管理者，原管理者降店长；原有店长不受影响。"""
    transfer = await _create_transfer(client, world, world.m2)

    r = await client.post(
        f"/transfers/{transfer['id']}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "manager"
    assert r.json()["store"]["id"] == world.s1_id

    db_session.expire_all()
    roles = _role_map(db_session, world.s1_id)
    assert roles[world.m2.user_id] == "manager"    # 新管理者
    assert roles[world.m.user_id] == "store_manager"   # 原管理者降店长
    assert roles[world.sm.user_id] == "store_manager"  # 原店长不受影响
    assert roles[world.sm2.user_id] == "store_manager"
    assert _manager_ids(db_session, world.s1_id) == {world.m2.user_id}  # 恰 1 管理者


async def test_t_tr_01_target_already_store_manager_promoted(client, world, db_session: Session):
    """AC-TR-01 变体：目标已是本店店长 → 其行升格为管理者；店长总数不变。"""
    sm_row = (
        db_session.query(Membership)
        .filter(Membership.store_id == world.s1_id, Membership.user_id == world.sm.user_id)
        .one()
    )
    transfer = await _create_transfer(client, world, world.sm)

    r = await client.post(
        f"/transfers/{transfer['id']}/accept",
        json={"version": 1},
        headers=bearer(world.sm.token),
    )
    assert r.status_code == 200, r.text

    db_session.expire_all()
    promoted = db_session.get(Membership, sm_row.id)   # 同一行升格，非新建
    assert promoted.role == "manager"
    roles = _role_map(db_session, world.s1_id)
    assert roles[world.m.user_id] == "store_manager"
    assert roles[world.sm2.user_id] == "store_manager"  # 其余店长不动
    assert _manager_ids(db_session, world.s1_id) == {world.sm.user_id}
    total = (
        db_session.query(Membership).filter(Membership.store_id == world.s1_id).count()
    )
    assert total == 3   # 成员数不变（升格而非新增）


async def test_t_tr_02_stale_transfer_conflict(client, world, db_session: Session):
    """AC-TR-02 过期案：发起人已非管理者 → 接受 409 seat_conflict，席位不变。"""
    # 先完成一次转让：m2 接管，m 降店长
    transfer = await _create_transfer(client, world, world.m2)
    r = await client.post(
        f"/transfers/{transfer['id']}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 200

    # 数据层构造过期待接受转让（from_user=m 已非管理者）
    stale = Transfer(
        store_id=world.s1_id,
        from_user_id=world.m.user_id,
        to_user_id=world.sm2.user_id,
        status="pending",
        version=1,
    )
    db_session.add(stale)
    db_session.commit()

    r = await client.post(
        f"/transfers/{stale.id}/accept",
        json={"version": 1},
        headers=bearer(world.sm2.token),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "seat_conflict"

    db_session.expire_all()
    assert _manager_ids(db_session, world.s1_id) == {world.m2.user_id}   # 恰 1 管理者，席位不变
    assert db_session.get(Transfer, stale.id).status == "pending"        # one-shot 回滚


async def test_t_tr_02_double_accept_one_success(client, world, db_session: Session):
    """AC-TR-02 并发案（双会话先后接受同一转让）：仅一方成功，恰 1 管理者。"""
    transfer = await _create_transfer(client, world, world.m2)

    r1 = await client.post(
        f"/transfers/{transfer['id']}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r1.status_code == 200

    # 第二会话（同目标旧 version）再接受 → 409 already_processed，零副作用
    r2 = await client.post(
        f"/transfers/{transfer['id']}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "already_processed"

    db_session.expire_all()
    assert _manager_ids(db_session, world.s1_id) == {world.m2.user_id}
    assert _role_map(db_session, world.s1_id)[world.m.user_id] == "store_manager"


async def test_t_tr_02_only_one_pending_per_store(client, world):
    """AC-TR-02：本店已有一笔待接受转让 → 再发起 409 pending_exists。"""
    await _create_transfer(client, world, world.m2)
    r = await client.post(
        f"/stores/{world.s1_id}/transfers",
        json={"phone": world.sm.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "pending_exists"


async def test_t_tr_self_transfer_rejected(client, world):
    """AC-TR（边界）：管理者转让给自己 → 422 self_transfer。"""
    r = await client.post(
        f"/stores/{world.s1_id}/transfers",
        json={"phone": world.m.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "self_transfer"


async def test_t_tr_03_pending_transfer_keeps_seats(client, world, db_session: Session):
    """AC-TR-03：转让待处理期间席位不变。"""
    transfer = await _create_transfer(client, world, world.m2)
    assert transfer["status"] == "pending"

    db_session.expire_all()
    assert _manager_ids(db_session, world.s1_id) == {world.m.user_id}
    roles = _role_map(db_session, world.s1_id)
    assert world.m2.user_id not in roles     # 被转让方门店角色不变（尚非成员）

    # 目标可见待接受转让（GET /invites）
    r = await client.get("/invites", headers=bearer(world.m2.token))
    assert r.status_code == 200
    assert any(t["id"] == transfer["id"] for t in r.json()["transfers"])
