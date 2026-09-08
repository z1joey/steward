"""Domain errors → HTTP mapping (B-specs §0.2/§0.4).

统一错误体：{"detail": "<机器码或中文文案>"}。
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppError(Exception):
    status_code: int = 400
    detail: str = "error"

    def __init__(self, detail: str | None = None, status_code: int | None = None) -> None:
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class Unauthorized(AppError):
    status_code = 401
    detail = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    detail = "forbidden"


class NotFound(AppError):
    status_code = 404
    detail = "not_found"


class BusinessError(AppError):
    """业务规则违规 → 422（分红超额、自转让、周期非 month 等）。"""

    status_code = 422
    detail = "business_rule"


class Conflict(AppError):
    """可预期唯一性/状态冲突 → 409，机器码由调用方给出
    （phone_taken / already_member / pending_exists 等）。"""

    status_code = 409
    detail = "conflict"


class VersionConflict(AppError):
    """乐观锁冲突 → 409（客户端 toast「已被别人更新，已刷新」）。"""

    status_code = 409
    detail = "version_conflict"


class SeatConflict(AppError):
    """席位冲突 → 409（转让过期 / 并发接受抢占管理者位）。"""

    status_code = 409
    detail = "seat_conflict"


class AlreadyProcessed(AppError):
    """one-shot 已执行 → 409。"""

    status_code = 409
    detail = "already_processed"


class InsufficientBalance(AppError):
    """公账余额不足（分红 require_sufficient_balance）→ 422，事务回滚零副作用。"""

    status_code = 422
    detail = "insufficient_balance"


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        # 兜底：partial unique（一店恰 1 管理者）等完整性冲突 → 409（B-specs §0.4）。
        # 各 service 对可预期冲突（already_member / pending_exists / phone_taken）
        # 在此之前自行捕获并映射为更精确的机器码。
        return JSONResponse(status_code=409, content={"detail": "seat_conflict"})
