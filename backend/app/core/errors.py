from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _response(request: Request, *, status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorBody(
        code=code,
        message=message,
        details=details,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="请求参数不符合要求",
            details=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = "请求的资源不存在" if exc.status_code == 404 else str(exc.detail)
        return _response(request, status_code=exc.status_code, code=code, message=message)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        get_logger(__name__).exception("unhandled_error", extra={"request_id": _request_id(request)})
        return _response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="服务暂时不可用",
        )
