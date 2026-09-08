"""T-INV-01~04（AC-INV-01~05）。多店长并存 / already_member / pending_exists。"""

from sqlalchemy.orm import Session

from app.modules.memberships.models import Membership
from tests.helpers import bearer, invite_and_accept, register_and_login, unique_phone


async def test_t_inv_01_invite_registered_pending(client, world):
    """AC-INV-01/02：M 邀已注册手机号 → pending；未接受前对方店列表无本店。"""
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["invitee"]["phone"] == world.m2.phone

    # 未接受前：被邀用户的门店列表不含本店（AC-INV-02）
    r = await client.get("/stores", headers=bearer(world.m2.token))
    assert r.status_code == 200
    assert all(item["id"] != world.s1_id for item in r.json()["items"])

    # 被邀用户可见 pending 邀请（含邀请人手机号）
    r = await client.get("/invites", headers=bearer(world.m2.token))
    assert r.status_code == 200
    invites = r.json()["invites"]
    assert any(
        i["store"]["id"] == world.s1_id and i["inviter_phone"] == world.m.phone
        for i in invites
    )

    # 未注册手机号 → 404 phone_not_registered（Locked：必须已注册）
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": "10000000000"},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "phone_not_registered"


async def test_t_inv_02_accept_becomes_store_manager(client, world):
    """AC-INV-03：接受后 role=店长，门店出现在选择器数据中。"""
    await invite_and_accept(client, world.m.token, world.s1_id, world.m2)

    r = await client.get("/stores", headers=bearer(world.m2.token))
    assert r.status_code == 200
    stores = {item["id"]: item for item in r.json()["items"]}
    assert stores[world.s1_id]["role"] == "store_manager"


async def test_t_inv_03_multiple_store_managers_and_rejections(client, world, db_session: Session):
    """AC-INV-04：店长不限人数（并存）；邀请已是成员 / 重复待接受 → 拒绝。"""
    # world 里 S1 已有 sm、sm2 两位店长并存
    managers = (
        db_session.query(Membership)
        .filter(Membership.store_id == world.s1_id, Membership.role == "store_manager")
        .all()
    )
    assert {m.user_id for m in managers} == {world.sm.user_id, world.sm2.user_id}

    # 邀请已是本店成员（sm）→ 409 already_member
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.sm.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "already_member"

    # 同一人重复待接受邀请 → 409 pending_exists
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "pending_exists"

    # 第三人接受已有待接受邀请后三位店长并存
    r = await client.get("/invites", headers=bearer(world.m2.token))
    invite_id = next(
        i["id"] for i in r.json()["invites"] if i["store"]["id"] == world.s1_id
    )
    r = await client.post(
        f"/invites/{invite_id}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 200, r.text
    count = (
        db_session.query(Membership)
        .filter(Membership.store_id == world.s1_id, Membership.role == "store_manager")
        .count()
    )
    assert count == 3


async def test_t_inv_04_store_manager_cannot_invite(client, world):
    """AC-INV-05：店长无邀请入口；API 调用 403 forbidden_role。"""
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.sm.token, world.s1_id),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "forbidden_role"


async def test_t_inv_reject_flow_then_accept_processed(client, world):
    """拒绝流（TA-06 已实现）：非受邀人 403 · 拒绝 200 rejected · 再接受 409 已处理。"""
    r = await client.post(
        f"/stores/{world.s1_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),
    )
    assert r.status_code == 201, r.text
    invite_id = r.json()["id"]

    # 非受邀人（sm）拒绝 → 403 not_invitee
    r = await client.post(
        f"/invites/{invite_id}/reject",
        json={"version": 1},
        headers=bearer(world.sm.token),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "not_invitee"

    # 受邀人拒绝 → 200 rejected
    r = await client.post(
        f"/invites/{invite_id}/reject",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    # 拒绝后接受 → 409 already_processed；门店列表仍无本店（拒绝不产生 membership）
    r = await client.post(
        f"/invites/{invite_id}/accept",
        json={"version": 1},
        headers=bearer(world.m2.token),
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "already_processed"
    r = await client.get("/stores", headers=bearer(world.m2.token))
    assert all(item["id"] != world.s1_id for item in r.json()["items"])


async def test_t_iso_01_invite_path_store_id_must_match_header(client, world):
    """路径 :store_id 与 X-Store-Id 不一致 → 按跨店资源 404。"""
    r = await client.post(
        f"/stores/{world.s2_id}/invites",
        json={"phone": world.m2.phone},
        headers=bearer(world.m.token, world.s1_id),   # header 指向 S1，路径指向 S2
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "not_found"
