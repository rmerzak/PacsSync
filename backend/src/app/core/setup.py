from typing import Any
from fastapi import APIRouter, Depends, FastAPI
import anyio
import fastapi
import psycopg2
from .config import (
    AppSettings,
    EnvironmentSettings,
    EnvironmentOption,
    settings,
)
from app.core.logger import logging
from psycopg2 import sql

logger = logging.getLogger(__name__)


async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = number_of_tokens


def create_application(
    router: APIRouter,
    settings: (
        AppSettings
        | EnvironmentSettings
    ),
    create_tables_on_start: bool = True,
    **kwargs: Any,
) -> FastAPI:
    application = FastAPI(**kwargs)

    application.include_router(router)
    application.add_event_handler("startup", set_threadpool_tokens)
    
    if isinstance(settings, EnvironmentSettings):
        docs_router = APIRouter()

        if settings.ENVIRONMENT != EnvironmentOption.PRODUCTION or settings.ENVIRONMENT != EnvironmentOption.DEVELOPMENT:
            if settings.ENVIRONMENT != EnvironmentOption.LOCAL:
                docs_router = APIRouter(dependencies=[Depends(get_current_superuser)])
                
            @docs_router.get("/docs", include_in_schema=False)
            async def get_swagger_documentation() -> fastapi.responses.HTMLResponse:
                return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/redoc", include_in_schema=False)
            async def get_redoc_documentation() -> fastapi.responses.HTMLResponse:
                return get_redoc_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/openapi.json", include_in_schema=False)
            async def openapi() -> dict[str, Any]:
                out: dict = get_openapi(title=application.title, version=application.version, routes=application.routes)
                return out

            application.include_router(docs_router)

    return application
