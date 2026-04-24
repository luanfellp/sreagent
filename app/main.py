from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.alerts import router as alerts_router
from app.api.postmortems import router as postmortems_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(alerts_router)
    app.include_router(postmortems_router)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        # import lazily so the app can start even if prometheus_client is not installed yet
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        data = generate_latest()
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
