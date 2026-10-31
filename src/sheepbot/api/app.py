import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from sheepbot.api import texts
from sheepbot.api.routers import clients, health, me, payments
from sheepbot.config import get_settings
from sheepbot.db.session import get_engine

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.dev_auth_enabled:
        logger.warning(
            "DEV AUTH ENABLED: requests without initData act as Telegram user %s. "
            "Never use on a server.",
            settings.dev_auth_telegram_id,
        )
    yield
    await get_engine().dispose()


def _field_path(loc: tuple[int | str, ...]) -> str:
    """("body", "sales", 3, "gross_kg") -> "sales[3].gross_kg"."""
    path = ""
    for part in loc[1:]:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else part
    return path


async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = texts.NOT_FOUND if exc.detail == "Not Found" else exc.detail
    return JSONResponse({"detail": detail}, exc.status_code, headers=exc.headers)


def _field_message(error: dict) -> str:
    if error["type"] == "value_error":
        return str(error["ctx"]["error"])
    template = texts.VALIDATION_MESSAGES.get(error["type"], texts.VALIDATION_DEFAULT)
    return template.format(**error.get("ctx", {}))


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = {_field_path(tuple(e["loc"])): _field_message(e) for e in exc.errors()}
    return JSONResponse(
        {"detail": texts.INVALID_INPUT, "fields": fields},
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def _server_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse({"detail": texts.SERVER_ERROR}, status.HTTP_500_INTERNAL_SERVER_ERROR)


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built Mini App; unknown non-API paths get index.html (client-side routing)."""
    index = dist / "index.html"
    if not index.is_file():
        logger.info("Frontend build not found at %s; serving the API only", dist)
        return
    root = dist.resolve()
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sheepbot API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _server_error)
    app.include_router(health.router, prefix=API_PREFIX, tags=["system"])
    app.include_router(me.router, prefix=API_PREFIX, tags=["me"])
    app.include_router(clients.router, prefix=API_PREFIX, tags=["clients"])
    app.include_router(payments.router, prefix=API_PREFIX, tags=["payments"])
    _mount_frontend(app, get_settings().web_dist_dir)
    return app


app = create_app()
