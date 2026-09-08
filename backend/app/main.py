from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Steward·司舵")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
