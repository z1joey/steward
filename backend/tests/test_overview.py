"""TE-T1 · T-OV-01（testing.md §3，AC-OV-01/02）：概览仅当前店；无 /hq/* 路由。"""

from tests.helpers import bearer


async def test_t_ov_01_overview_store_isolation(client, world):
    """AC-OV-01/02：S1/S2 概览数据不串；仅当前 X-Store-Id 店 KPI。"""
    h1 = bearer(world.m.token, world.s1_id)
    h2 = bearer(world.m.token, world.s2_id)

    # S1 产生支出 + pending 报销；S2 产生不同支出
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-01", "amount": "111", "memo": "S1支出",
              "needs_reimbursement": False},
        headers=h1,
    )
    assert r.status_code == 201
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-02", "amount": "77", "memo": "S1待审",
              "needs_reimbursement": True},
        headers=h1,
    )
    assert r.status_code == 201
    r = await client.post(
        "/ledger/entries",
        json={"date": "2026-09-03", "amount": "222", "memo": "S2支出",
              "needs_reimbursement": False},
        headers=h2,
    )
    assert r.status_code == 201

    r = await client.get("/overview?month=2026-09", headers=h1)
    assert r.status_code == 200, r.text
    ov1 = r.json()
    assert ov1["store"]["id"] == world.s1_id
    assert ov1["expense"] == "111.00"
    assert ov1["income"] == "0.00"
    assert ov1["pending_claims"]["count"] == 1
    assert ov1["pending_claims"]["amount"] == "77.00"
    assert ov1["public_balance"] == "0.00"      # manual 不动公账（O-05）

    r = await client.get("/overview?month=2026-09", headers=h2)
    ov2 = r.json()
    assert ov2["store"]["id"] == world.s2_id
    assert ov2["expense"] == "222.00"           # 不串
    assert ov2["pending_claims"]["count"] == 0

    # 无 membership 的 X-Store-Id → 403
    r = await client.get("/overview", headers=bearer(world.m2.token, world.s1_id))
    assert r.status_code == 403


async def test_t_ov_02_no_hq_routes(client, world):
    """AC-OV-02（Locked 不做）：无任何 /hq/* 跨店路由。"""
    h = bearer(world.m.token, world.s1_id)
    for path in ("/hq/overview", "/hq", "/hq/stores"):
        r = await client.get(path, headers=h)
        assert r.status_code == 404, (path, r.status_code)
