import logging
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Self

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import Settings, get_settings
from app.core.database import session_manager
from app.core.exceptions import AppException
from app.dependencies.redis import get_redis_client
from app.models import *  # noqa: F403

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.ERROR)


class FastApp(FastAPI):
    def __init__(self, settings: Settings, **kwargs: Any):
        self.settings = settings
        kwargs.setdefault("lifespan", self._lifespan)
        super().__init__(**kwargs)

    @asynccontextmanager
    async def _lifespan(self, _: Self, /) -> AsyncGenerator[None, Any]:
        redis_client = get_redis_client()
        await redis_client.connect()
        yield
        await session_manager.close()
        await redis_client.disconnect()

    def _setup_middlewares(self) -> None:
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routers(self) -> None:
        self.include_router(api_router)

    def _setup_exception_handlers(self) -> None:
        tb_str = traceback.format_exc()

        def exception_handler(exc: Exception):
            if isinstance(exc, AppException):
                content = exc.dict()
            elif isinstance(exc, HTTPException):
                content = AppException(status_code=exc.status_code, message=exc.detail).dict()
            else:
                message = str(exc) if self.settings.ENV == "dev" else "Internal Server Error"
                content = AppException(status_code=500, message=message).dict()

            status_code = getattr(exc, "status_code", 500)

            return JSONResponse(content=content, status_code=status_code)

        @self.exception_handler(Exception)
        async def global_handler(request: Request, exc: Exception):
            logger.error(
                f"Method: {request.method}. Request Failed: URL: {request.url}. Error: {str(exc)}. Traceback:\n{tb_str}"
            )
            return exception_handler(exc)

        @self.exception_handler(HTTPException)
        async def http_handler(request: Request, exc: HTTPException):
            logger.error(f"Exception at handler: {exc}")

            logger.error(
                f"Method: {request.method}. Request Failed: URL: {request.url}. Error: {str(exc)}. Traceback:\n{tb_str}"
            )
            return exception_handler(exc)

    def setup(self) -> None:
        super().setup()

        self._setup_exception_handlers()
        self._setup_middlewares()
        self._setup_routers()


app = FastApp(settings=get_settings())
