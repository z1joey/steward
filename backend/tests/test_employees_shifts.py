"""TD-T2 · T-EMP-01~04 + 跨店 404（testing.md §3，AC-EMP-01~05 · AC-ISO-02）。"""

from datetime import date, timedelta

from tests.helpers import bearer


async def _create_employee(client, h, name: str, job_type: str) -> dict:
    r = await client.post(
        "/employees",
        json={"name": name, "contact": "13800000000", "job_type": job_type, "notes": ""},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_t_emp_01_roster_columns_and_five_job_types(client, world, db_session):
    """AC-EMP-01：花名册字段齐全；job_type ∈ 五值。"""
    h = bearer(world.m.token, world.s1_id)
    jobs = ["long_term", "summer", "winter", "weekend", "temporary"]
    for i, job in enumerate(jobs):
        await _create_employee(client, h, f"员工{i}", job)
    r = await client.get("/employees", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert {i["job_type"] for i in items} == set(jobs)
    row = items[0]
    for field in ("id", "name", "status", "display_status", "contact", "job_type", "notes", "version"):
        assert field in row
    # 非法工种 → 422
    r = await client.post(
        "/employees", json={"name": "X", "job_type": "intern"}, headers=h
    )
    assert r.status_code == 422


async def test_t_emp_02_list_has_no_leave_fields_detail_does(client, world, db_session):
    """AC-EMP-02：列表接口无请假记录；详情子资源含 leaves。"""
    h = bearer(world.m.token, world.s1_id)
    emp = await _create_employee(client, h, "张三", "long_term")
    r = await client.get("/employees", headers=h)
    row = r.json()["items"][0]
    assert "leaves" not in row

    today = date.today().isoformat()
    r = await client.post(
        f"/employees/{emp['id']}/leaves",
        json={"start_date": today, "end_date": today, "note": "事假"},
        headers=h,
    )
    assert r.status_code == 201
    r = await client.get(f"/employees/{emp['id']}", headers=h)
    assert len(r.json()["leaves"]) == 1
    # 当日在假 → display_status=on_leave
    assert r.json()["display_status"] == "on_leave"
    # 列表仍不出现请假数据
    r = await client.get("/employees", headers=h)
    assert "leaves" not in r.json()["items"][0]


async def test_t_emp_03_multiple_segments_same_day(client, world, db_session):
    """AC-EMP-04：同日多段 → 各段 minutes 正确（日合计 UI 层求和）。"""
    h = bearer(world.m.token, world.s1_id)
    emp = await _create_employee(client, h, "张三", "long_term")
    today = date.today()
    for start, end in (("10:00", "14:00"), ("18:00", "20:00")):
        r = await client.post(
            "/shift_segments",
            json={
                "employee_id": emp["id"],
                "start_at": f"{today.isoformat()}T{start}:00",
                "end_at": f"{today.isoformat()}T{end}:00",
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
    week = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
    r = await client.get(f"/shift_segments?week={week}", headers=h)
    items = [i for i in r.json()["items"] if i["employee_id"] == emp["id"]]
    assert sorted(i["minutes"] for i in items) == [120, 240]   # 4h + 2h


async def test_t_emp_04_resigned_hidden_unless_segments(client, world, db_session):
    """AC-EMP-05：已离职默认隐藏；本周有段仍显示（服务端 employees 决定）。"""
    h = bearer(world.m.token, world.s1_id)
    e1 = await _create_employee(client, h, "无班离职", "weekend")
    e2 = await _create_employee(client, h, "有班离职", "weekend")
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": e2["id"],
            "start_at": f"{monday.isoformat()}T09:00:00",
            "end_at": f"{monday.isoformat()}T10:00:00",
        },
        headers=h,
    )
    assert r.status_code == 201
    for e in (e1, e2):
        r = await client.post(
            f"/employees/{e['id']}/resign",
            json={"effective_on": today.isoformat(), "version": e["version"]},
            headers=h,
        )
        assert r.status_code == 200

    # 默认花名册：两名离职者都不出现
    r = await client.get("/employees", headers=h)
    assert r.json()["items"] == []
    r = await client.get("/employees?include_resigned=true", headers=h)
    assert len(r.json()["items"]) == 2

    # 周排班：active ∪ 本周有段 → 仅 e2 可见
    week = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"
    r = await client.get(f"/shift_segments?week={week}", headers=h)
    emp_ids = [x["id"] for x in r.json()["employees"]]
    assert emp_ids == [e2["id"]]


async def test_t_emp_cross_store_ids_404(client, world, db_session):
    """AC-ISO-02：跨店 employee_id / segment_id → 404。"""
    h1 = bearer(world.m.token, world.s1_id)
    h2 = bearer(world.m.token, world.s2_id)
    emp = await _create_employee(client, h1, "张三", "long_term")
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": emp["id"],
            "start_at": "2026-09-07T10:00:00",
            "end_at": "2026-09-07T12:00:00",
        },
        headers=h1,
    )
    assert r.status_code == 201
    seg_id = r.json()["id"]

    # S2 访问 S1 的员工/班次
    r = await client.get(f"/employees/{emp['id']}", headers=h2)
    assert r.status_code == 404
    r = await client.put(
        f"/employees/{emp['id']}", json={"version": 1, "name": "X"}, headers=h2
    )
    assert r.status_code == 404
    r = await client.put(
        f"/shift_segments/{seg_id}",
        json={"version": 1, "start_at": "2026-09-07T10:00:00", "end_at": "2026-09-07T13:00:00"},
        headers=h2,
    )
    assert r.status_code == 404
    r = await client.request(
        "DELETE", f"/shift_segments/{seg_id}", json={"version": 1}, headers=h2
    )
    assert r.status_code == 404

    # S1 的 shift POST 引用 S1 员工在 S2 店上下文 → 404（员工跨店）
    r = await client.post(
        "/shift_segments",
        json={
            "employee_id": emp["id"],
            "start_at": "2026-09-07T10:00:00",
            "end_at": "2026-09-07T11:00:00",
        },
        headers=h2,
    )
    assert r.status_code == 404
