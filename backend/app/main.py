from fastapi import FastAPI

from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.claims.router import router as claims_router
from app.modules.dividend.router import router as dividend_router
from app.modules.employees.router import router as employees_router
from app.modules.invites.router import router as invites_router
from app.modules.ledger.router import router as ledger_router
from app.modules.memberships.router import router as memberships_router
from app.modules.overview.router import router as overview_router
from app.modules.payroll.router import router as payroll_router
from app.modules.public_account.router import router as public_account_router
from app.modules.recurring.router import router as recurring_router
from app.modules.shifts.router import router as shifts_router
from app.modules.stats.router import router as stats_router
from app.modules.stores.router import router as stores_router
from app.modules.transfers.router import router as transfers_router


def create_app() -> FastAPI:
    app = FastAPI(title="Steward·司舵")
    register_exception_handlers(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(stores_router)
    app.include_router(invites_router)
    app.include_router(transfers_router)
    app.include_router(memberships_router)
    app.include_router(ledger_router)
    app.include_router(claims_router)
    app.include_router(recurring_router)
    app.include_router(stats_router)
    app.include_router(dividend_router)
    app.include_router(employees_router)
    app.include_router(shifts_router)
    app.include_router(payroll_router)
    app.include_router(public_account_router)
    app.include_router(overview_router)
    return app


app = create_app()
