from functools import partial

from django.http import HttpRequest, JsonResponse, HttpResponse
from django.urls import path
from rest_framework import status

from .base import (
    HealthHandler, HealthTypesType, HEALTH_STATUS 
)


__all__ = ("get_url_pattern",)


def health_view(
    health_handler: HealthHandler,
    request: HttpRequest,
    type_: HealthTypesType,
    *args,
    **kwargs,
) -> JsonResponse:
    function = health_handler.get_method_by_type(type_)
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
    

def get_url_pattern(
    health_handler: HealthHandler,
) -> path:
    return path("health/<str:type_>/", partial(health_view, health_handler))

