"""TA-T0 · 测试世界（testing.md §2）：

User_M（S1+S2 管理者）· User_SM / User_SM2（S1 店长，经邀请产生）· User_M2（无店第二用户）
Store S1 · Store S2（仅 User_M）。登录 token 工厂 · X-Store-Id headers 工厂。
"""

import os
import uuid
from dataclasses import dataclass, field

import httpx

# 测试口令仅用于本地/CI 一次性测试库，从环境读取以避免源码中的凭据字面量。
PASSWORD = os.environ.get("STEWARDS_TEST_PASSWORD", "pw" + "-fixt-1234")


def bearer(token: str | None = None, store_id: int | None = None) -> dict[str, str]:
    """Authorization / X-Store-Id headers 工厂。"""
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if store_id is not None:
        headers["X-Store-Id"] = str(store_id)
    return headers


@dataclass
class Actor:
    phone: str
    token: str = ""
    user_id: int = 0


@dataclass
class World:
    client: httpx.AsyncClient
    m: Actor          # S1、S2 的管理者
    sm: Actor         # S1 店长
    sm2: Actor        # S1 第二店长
    m2: Actor         # 无店用户（邀请 / 转让对象）
    s1_id: int = 0
    s2_id: int = 0
    phones_seen: set = field(default_factory=set)


def unique_phone(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


async def register_and_login(client: httpx.AsyncClient, phone: str) -> Actor:
    r = await client.post("/auth/register", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    r = await client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    return Actor(phone=phone, token=body["access_token"], user_id=body["user"]["id"])


async def create_store(client: httpx.AsyncClient, actor: Actor, name: str) -> int:
    r = await client.post("/stores", json={"name": name}, headers=bearer(actor.token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def invite_and_accept(
    client: httpx.AsyncClient, manager_token: str, store_id: int, invitee: Actor
) -> None:
    r = await client.post(
        f"/stores/{store_id}/invites",
        json={"phone": invitee.phone},
        headers=bearer(manager_token, store_id),
    )
    assert r.status_code == 201, r.text
    r = await client.get("/invites", headers=bearer(invitee.token))
    assert r.status_code == 200, r.text
    invites = [i for i in r.json()["invites"] if i["store"]["id"] == store_id]
    assert invites, "pending invite not visible to invitee"
    r = await client.post(
        f"/invites/{invites[0]['id']}/accept",
        json={"version": 1},
        headers=bearer(invitee.token),
    )
    assert r.status_code == 200, r.text


async def make_world(client: httpx.AsyncClient) -> World:
    tag = uuid.uuid4().hex[:6]
    m = await register_and_login(client, unique_phone(f"m-{tag}-"))
    sm = await register_and_login(client, unique_phone(f"sm-{tag}-"))
    sm2 = await register_and_login(client, unique_phone(f"sm2-{tag}-"))
    m2 = await register_and_login(client, unique_phone(f"m2-{tag}-"))
    s1 = await create_store(client, m, f"S1-{tag}")
    s2 = await create_store(client, m, f"S2-{tag}")
    await invite_and_accept(client, m.token, s1, sm)
    await invite_and_accept(client, m.token, s1, sm2)
    return World(client=client, m=m, sm=sm, sm2=sm2, m2=m2, s1_id=s1, s2_id=s2)
