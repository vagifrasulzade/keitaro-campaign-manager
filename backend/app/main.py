import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, KeitaroError
from app.integrations.keitaro import FakeKeitaroClient, KeitaroClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("adrobot")


def build_keitaro_client(settings: Settings):
    if settings.keitaro_mock:
        logger.warning("KEITARO_MOCK=true → using in-memory fake Keitaro")
        return FakeKeitaroClient()
    return KeitaroClient(settings.keitaro_api_base, settings.keitaro_api_key, settings.keitaro_timeout)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if getattr(app.state, "keitaro", None) is None:  # tests inject their own client
        try:
            app.state.keitaro = build_keitaro_client(settings)
        except KeitaroError as exc:
            logger.error("Keitaro client not created: %s", exc.message)
            app.state.keitaro, app.state.keitaro_error = None, exc.message
    yield
    client = getattr(app.state, "keitaro", None)
    if hasattr(client, "aclose"):
        await client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)

    if settings.frontend_dir.exists():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
