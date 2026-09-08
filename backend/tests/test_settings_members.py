"""TA-T1（P0）· T-ISO-01（AC-ISO-01）+ TA-08 · GET /settings/members（US-F1 / AC-INV-05）。"""

from sqlalchemy.orm import Session

from app.modules.memberships.models import Membership
from tests.helpers import bearer


async def test_t_iso_01_store_header_without_membership(client, world):
    """AC-ISO-01：带 S1 的 token + X-Store-Id=S2（无 membership）→ 读写失败 403。"""
    # m2 无 S1 membership：店级读 → 403 no_membership
    r = await client.get("/settings/members", headers=bearer(world.m2.token, world.s1_id))
    assert r.status_code == 403
    assert r.json()["detail"] == "no_membership"

    # 店级写（邀请）→ 403 no_membership
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m2.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "no_membership"

    # 缺头 / 非整数 X-Store-Id → 403
    r = await client.get("/settings/members", headers=bearer(world.m.token))
    assert r.status_code == 403
    r = await client.get(
        "/settings/members", headers=bearer(world.m.token, None) | {"X-Store-Id": "abc"}
    )
    assert r.status_code == 403

    # 对照：sm 是成员但非管理者 → 403 forbidden_role（先 membership 后角色）
    r = await client.get("/settings/members", headers=bearer(world.sm.token, world.s1_id))
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"


async def test_t_iso_01_user_m_manages_both_stores_isolated(client, world, db_session: Session):
    """User_M 对 S2 是管理者、对 S1 也是管理者；S2 只有其一人（testing.md §2）。"""
    db_session.expire_all()
    s2_members = (
        db_session.query(Membership).filter(Membership.store_id == world.s2_id).all()
    )
    assert [m.user_id for m in s2_members] == [world.m.user_id]
    assert s2_members[0].role == "manager"

    # S2 的成员接口只见 S2 成员
    r = await client.get("/settings/members", headers=bearer(world.m.token, world.s2_id))
    assert r.status_code == 200
    body = r.json()
    assert [mem["user"]["id"] for mem in body["members"]] == [world.m.user_id]


async def test_t_settings_members_lists_everything(client, world):
    """US-F1：成员 + pending 邀请 / 转让（manager only 已由 ISO 用例覆盖 403 侧）。"""
    # 造一笔 pending 邀请 + 一笔 pending 转让
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201
    r = await client.post(
        f"/stores/{world.s1_id}/transfers",
        json={"phone": world.sm.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201

    r = await client.get("/settings/members", headers=bearer(world.m.token, world.s1_id))
    assert r.status_code == 200
    body = r.json()

    assert len(body["members"]) == 3   # m + sm + sm2
    roles = {mem["user"]["id"]: mem["role"] for mem in body["members"]}
    assert roles[world.m.user_id] == "manager"
    assert roles[world.sm.user_id] == "store_manager"
    assert roles[world.sm2.user_id] == "store_manager"
    assert all(mem["since"] for mem in body["members"])

    assert len(body["pending_invites"]) == 1
    assert body["pending_invites"][0]["user"]["phone"] == world.m2.phone
    assert len(body["pending_transfers"]) == 1
    assert body["pending_transfers"][0]["user"]["phone"] == world.sm.phone
