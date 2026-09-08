from fastapi import FastAPI

from app.core.errors import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.invites.router import router as invites_router
from app.modules.memberships.router import router as memberships_router
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
    return app


app = create_app()
