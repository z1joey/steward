"""T-AUTH-01~03（AC-AUTH-01/02/03/04）。"""

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.stores.models import Ledger, PublicAccount
from tests.helpers import PASSWORD, bearer, register_and_login, unique_phone


async def test_t_auth_01_register_then_login(client):
    """AC-AUTH-01/02：注册 → 登录；重复手机号 409；错误凭证 401。"""
    phone = unique_phone("auth-")

    r = await client.post("/auth/register", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    assert r.json()["phone"] == phone

    # 重复手机号 → 拒绝（409 phone_taken）
    r = await client.post("/auth/register", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 409
    assert r.json()["detail"] == "phone_taken"

    r = await client.post("/auth/login", json={"phone": phone, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["access_token"]
    assert body["user"]["phone"] == phone

    # 错误凭证 → 401 invalid_credentials
    r = await client.post("/auth/login", json={"phone": phone, "password": PASSWORD + "-wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_credentials"

    # GET /me
    r = await client.get("/me", headers=bearer(body["access_token"]))
    assert r.status_code == 200
    assert r.json()["phone"] == phone

    # 无 token → 401 unauthorized
    r = await client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "unauthorized"


async def test_t_auth_02_login_without_store(client):
    """AC-AUTH-03（API 侧）：登录后无店 → 门店列表为空、无 pending。"""
    actor = await register_and_login(client, unique_phone("nostore-"))

    r = await client.get("/stores", headers=bearer(actor.token))
    assert r.status_code == 200
    assert r.json()["items"] == []

    r = await client.get("/invites", headers=bearer(actor.token))
    assert r.status_code == 200
    assert r.json()["invites"] == [] and r.json()["transfers"] == []


async def test_t_auth_03_create_store_txn(client, db_session: Session):
    """AC-AUTH-04：建店事务 → 管理者 membership + ledgers(UNIQUE store) + 公账初始 0。"""
    actor = await register_and_login(client, unique_phone("owner-"))

    r = await client.post(
        "/stores", json={"name": "司舵旗舰店"}, headers=bearer(actor.token)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "manager"
    store_id = body["id"]

    # 数据层断言（testing.md §1）：同事务三件套
    membership = (
        db_session.query(Membership)
        .filter(Membership.store_id == store_id, Membership.user_id == actor.user_id)
        .one_or_none()
    )
    assert membership is not None and membership.role == "manager"

    ledger = db_session.query(Ledger).filter(Ledger.store_id == store_id).one_or_none()
    assert ledger is not None

    account = (
        db_session.query(PublicAccount).filter(PublicAccount.store_id == store_id).one_or_none()
    )
    assert account is not None
    assert account.balance == 0

    user = db_session.get(User, actor.user_id)
    assert user is not None and user.phone == actor.phone
