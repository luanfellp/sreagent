from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from app.api.alerts import router as alerts_router
from app.api.dashboard import router as dashboard_router
from app.api.incidents import router as incidents_router
from app.api.postmortems import router as postmortems_router
from app.core.settings import get_settings
from app.dependencies import (
    build_kubernetes_client,
    build_loki_client,
    build_prometheus_client,
    build_telegram_notifier,
    build_whatsapp_notifier,
    close_client,
)
from app.services.incident_store import IncidentStore
from app.services.notification_service import NotificationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.read_only_mode:
        raise RuntimeError("SREAgent only supports read-only mode.")

    app.state.prometheus_client = build_prometheus_client()
    app.state.loki_client = build_loki_client()
    app.state.kubernetes_client = build_kubernetes_client(settings)
    app.state.incident_store = IncidentStore(
        max_records=settings.incident_history_limit
    )
    app.state.notification_service = NotificationService(
        build_telegram_notifier(settings),
        build_whatsapp_notifier(settings),
    )

    try:
        yield
    finally:
        close_client(app.state.prometheus_client)
        close_client(app.state.loki_client)
        close_client(app.state.kubernetes_client)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(alerts_router)
    app.include_router(dashboard_router)
    app.include_router(incidents_router)
    app.include_router(postmortems_router)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        # import lazily so the app can start even if prometheus_client is not installed yet
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        data = generate_latest()
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
