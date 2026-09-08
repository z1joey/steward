"""TF-01 · testing.md §4 角色拒绝矩阵（AC-ROLE-MATRIX）。

遍历 enums.MANAGER_ONLY 全部 7 项 × User_SM → 403 forbidden_role；
× User_M（同店）→ 非 403（席位/业务规则错误除外，如分红超额 422）。
"""

import pytest

from tests.helpers import PASSWORD, bearer, unique_phone

pytest.importorskip("httpx")


async def _register(client, prefix: str) -> tuple[str, str]:
    """注册并登录 → (phone, token)。"""
    phone = unique_phone(prefix)
    r = await client.post("/auth/register", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 201
    r = await client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 200
    return phone, r.json()["access_token"]


async def _invoke(client, world, capability: str, token: str):
    """以给定 token 在 S1 上下文调用能力对应路由。"""
    headers = bearer(token, world.s1_id)
    if capability == "invites.create":
        phone, _ = await _register(client, "inv-")
        return await client.post(
            f"/stores/{world.s1_id}/invites", json={"phone": phone}, headers=headers
        )
    if capability == "transfers.create":
        phone, _ = await _register(client, "tr-")
        return await client.post(
            f"/stores/{world.s1_id}/transfers", json={"phone": phone}, headers=headers
        )
    if capability in ("claims.approve", "claims.reject"):
        r = await client.post(
            "/ledger/entries",
            json={"date": "2026-09-02", "amount": "10", "memo": "m",
                  "needs_reimbursement": True},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        claim_id = r.json()["claim"]["id"]
        return await client.post(
            f"/claims/{claim_id}/{capability.split('.')[1]}",
            json={"version": 1},
            headers=headers,
        )
    if capability == "ledger.reverse":
        r = await client.post(
            "/ledger/entries",
            json={"date": "2026-09-02", "amount": "10", "memo": "m",
                  "needs_reimbursement": False},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        entry_id = r.json()["entry"]["id"]
        return await client.post(
            f"/ledger/entries/{entry_id}/reverse",
            json={"version": 1},
            headers=headers,
        )
    if capability == "payroll.settle":
        return await client.post("/payroll/settle", json={"month": "2099-01"}, headers=headers)
    if capability == "dividend.confirm":
        return await client.post(
            "/dividends/confirm",
            json={"amount": "1", "public_account_version": 1},
            headers=headers,
        )
    raise AssertionError(f"unknown capability {capability}")


@pytest.mark.parametrize(
    "capability", sorted(
        [
            "claims.approve",
            "claims.reject",
            "payroll.settle",
            "dividend.confirm",
            "ledger.reverse",
            "invites.create",
            "transfers.create",
        ]
    ),
    ids=str,
)
async def test_sm_denied_and_manager_allowed(client, world, capability: str):
    """§4：User_SM deny（403 forbidden_role）· User_M allow（非 403）。"""
    # deny：店长调用 → 403 forbidden_role
    r = await _invoke(client, world, capability, world.sm.token)
    assert r.status_code == 403, (capability, r.status_code, r.text)
    assert r.json()["detail"] == "forbidden_role"

    # allow：管理者同店调用 → 非 403（业务规则 409/422 亦为放行）
    r = await _invoke(client, world, capability, world.m.token)
    assert r.status_code != 403, (capability, r.status_code, r.text)
