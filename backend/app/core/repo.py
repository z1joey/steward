"""店级 Repo 基类与 one-shot 行数校验（B-specs §0.4）。

读取统一走 Session.get 主键 API（驱动参数化），不做动态表名拼接；
条件 UPDATE 由各模块以具体 Model 类构建（列引用均为映射属性，值经绑定参数下发）。
"""

from typing import ClassVar, TypeVar

from sqlalchemy.orm import Session

from app.core.errors import NotFound, VersionConflict

ModelT = TypeVar("ModelT")


class StoreScopedRepo:
    """店级资源基类：子类声明 `model`。

    get(store_id, id)：主键读取后校验归属；不存在 / 跨店 → 404 not_found
    （B-specs §0.4：跨店资源一律 404）。
    """

    model: ClassVar[type]

    @classmethod
    def get(cls, db: Session, store_id: int, row_id: int):
        row = db.get(cls.model, row_id)
        if row is None or row.store_id != store_id:
            raise NotFound()
        return row


def ensure_one_shot(rowcount: int | None) -> None:
    """one-shot 条件 UPDATE 的 rowcount 校验：≠1 → 409 version_conflict。

    各模块的条件 UPDATE 语句自带 status/持有人/version 等条件；
    rowcount≠1 时再回读行区分 403 / already_processed / version_conflict。
    """
    if rowcount != 1:
        raise VersionConflict()
