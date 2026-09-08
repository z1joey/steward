import os

# 测试库连接串必须在任何 app 模块导入前生效（settings 读环境变量）。
TEST_DATABASE_URL = os.environ.get(
    "STEWARDS_TEST_DATABASE_URL",
    "postgresql+psycopg://localhost/steward_test",
)
os.environ["STEWARDS_DATABASE_URL"] = TEST_DATABASE_URL

from collections.abc import AsyncIterator, Iterator  # noqa: E402

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.db import get_db
from app.main import create_app

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """真 Postgres 测试库；session 级执行迁移（testing.md §1）。"""
    cfg = Config(os.path.join(BACKEND_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_ROOT, "alembic"))
    command.upgrade(cfg, "head")
    yield create_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
def db_connection(engine: Engine) -> Iterator[object]:
    """每测试一个连接 + 外层事务；结束时整体 ROLLBACK（T0-12：每测试事务回滚）。"""
    conn = engine.connect()
    tx = conn.begin()
    yield conn
    tx.rollback()
    conn.close()


def _test_session_factory(conn) -> sessionmaker[Session]:
    # create_savepoint：被测代码内部 commit/rollback 只作用于保存点，外层事务保留
    return sessionmaker(bind=conn, join_transaction_mode="create_savepoint")


@pytest.fixture
def db_session(db_connection) -> Iterator[Session]:
    """供测试做数据层断言（testing.md §1 数据层），与被测请求同事务可见。"""
    session = _test_session_factory(db_connection)()
    yield session
    session.close()


@pytest.fixture
def app(db_connection) -> FastAPI:
    fastapi_app = create_app()
    factory = _test_session_factory(db_connection)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def world(client: httpx.AsyncClient):
    """TA-T0：User_M/SM/SM2/M2 + Store S1/S2（testing.md §2）。"""
    from tests.helpers import make_world

    return await make_world(client)
