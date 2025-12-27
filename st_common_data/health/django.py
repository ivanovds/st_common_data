from typing import Callable
from functools import partial

from django.http import JsonResponse, HttpResponse
from rest_framework import status

from .base import (
    HealthHandler, HealthTypesType, HEALTH_STATUS 
)


__all__ = ("get_middleware",)


path_type_mapper: dict[str, HealthTypesType] = {
    "/health/ready/": "ready",
    "/health/live/": "live",
    "/health/startup/": "startup",
}


def health_middleware(
    health_handler: HealthHandler,
    get_response,
) -> JsonResponse:
    def inner(request):
        # remove after gcp migration
        if request.path == "/health":
            return JsonResponse(status=status.HTTP_200_OK, data={"ok": True})

        if request.path not in path_type_mapper.keys():
            return get_response(request)

        function = health_handler.get_method_by_type(path_type_mapper[request.path])
        display = request.GET.get("display", False)

        status_ = function()

        if status_["status"] == HEALTH_STATUS.UNHEALTHY.value:
            if display:
                return JsonResponse(status=status.HTTP_503_SERVICE_UNAVAILABLE, data=status_)
            else:
                return HttpResponse(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if display:
            return JsonResponse(status=status.HTTP_200_OK, data=status_)
        else:
            return HttpResponse(status=status.HTTP_200_OK)

    return inner


def get_middleware(
    health_handler: HealthHandler,
) -> Callable:
    return partial(health_middleware, health_handler)
