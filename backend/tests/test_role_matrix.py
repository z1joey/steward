"""TA-T3 · testing.md §4 角色拒绝矩阵（本分支可测项）。

对 User_SM + Store S1 deny（403 forbidden_role）；对 User_M 同店 allow。
矩阵其余能力（claims / payroll / dividend / ledger.reverse）随对应任务分支补齐，
此处遍历 enums.MANAGER_ONLY 中已落地路由的两个操作。
"""

import pytest

from tests.helpers import PASSWORD, bearer, unique_phone

# (能力 ID, 路径)
OPS = [
    ("invites.create", "invites"),
    ("transfers.create", "transfers"),
]


async def _invoke(client, path: str, token: str, store_id: int, phone: str):
    return await client.post(
        f"/stores/{store_id}/{path}",
        json={"phone": phone},
        headers=bearer(token, store_id),
    )


@pytest.mark.parametrize("capability,path", OPS, ids=[c for c, _ in OPS])
async def test_sm_denied_and_manager_allowed(client, world, capability, path):
    """§4：User_SM deny · User_M allow（席位冲突场景除外）。"""
    # deny：店长调用 → 403 forbidden_role
    r = await _invoke(client, path, world.sm.token, world.s1_id, world.m2.phone)
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "forbidden_role"

    # allow：管理者同店调用（对方需已注册）→ 201
    phone = unique_phone(f"{path}-")
    r = await client.post("/auth/register", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    r = await _invoke(client, path, world.m.token, world.s1_id, phone)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending"
