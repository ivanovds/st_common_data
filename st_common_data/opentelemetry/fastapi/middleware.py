import traceback
import time
import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)

__all__ = ("CustomLoggerMiddleware",)


class CustomLoggerMiddleware(BaseHTTPMiddleware):
    def get_client_ip(self, request: Request) -> str:
        if request.client:
            return request.client.host
        return ""

    def make_extra(
        self,
        *,
        request: Request,
        response: Response,
    ) -> dict[str, str | dict[str, str]]:
        extra = {
            "request": {
                "method": request.scope["method"],
                "url": request.scope["path"],
                "query": request.scope["query_string"].decode("utf-8"),
            },
            "context": {
                "ip": self.get_client_ip(request),
                "userAgent": request.headers.get("user-agent"),
            },
            "response": {
                "statusCode": response.status_code,
            },
        }

        if exception := getattr(request, "exception", None):
            extra["traceback"] = "".join(traceback.format_exception(exception))  # type: ignore

        return extra

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            request.exception = e
            response = JSONResponse({"detail": "Internal error"}, status_code=500)

        seconds = time.perf_counter() - start

        extra = self.make_extra(
            request=request,
            response=response
        )
        extra["duration"] = "%.3fs" % seconds

        args = (
            "%s %s %s %.3fs",
            request.method,
            f"{request.url.path}?{request.url.query}",
            response.status_code,
            seconds,
        )
        kwargs = {
            "extra": {"extra": extra}
        }

        if response.status_code >= 500:
            logger.error(
                *args,
                **kwargs,
            )
        elif response.status_code >= 400:
            logger.warning(
                *args,
                **kwargs,
            )
        else:
            logger.info(
                *args,
                **kwargs,
            )

        return response

