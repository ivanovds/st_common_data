import logging
import time
import traceback

from django.http import HttpRequest, HttpResponse

__all__ = ('CustomLoggerMiddleware',)

logger = logging.getLogger(__name__)


class CustomLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_user_data(self, request: HttpRequest) -> dict[str, int | str | None]:
        if not hasattr(request, "user"):
            return {}

        return {
            "userId": getattr(request.user, "id", None),
            "userAuth0": getattr(request.user, "auth0", None),
        }

    def make_extra(
        self,
        *,
        request: HttpRequest,
        response: HttpResponse,
    ) -> dict[str, dict[str, str]]:
        extra = {
            "request": {
                "method": request.method,
                "url": request.path,
                "query": request.META.get("QUERY_STRING"),
            },
            "context": {
                "ip": self.get_client_ip(request),
                "userAgent": request.headers.get("User-Agent"),
                **self.get_user_data(request),
            },
            "response": {
                "statusCode": response.status_code,
            },
        }

        if exception := getattr(request, "exception", None):
            extra["traceback"] = "".join(traceback.format_exception(exception))  # type: ignore

        return extra

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpRequest:
        request.exception = exception
        return None

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)

        seconds = time.perf_counter() - start

        extra = self.make_extra(
            request=request,
            response=response
        )
        extra["duration"] = "%.3fs" % seconds

        args = (
            "%s %s %s %.3fs",
            request.method,
            request.get_full_path(),
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
