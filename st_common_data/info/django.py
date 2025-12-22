from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from .base import make_project_info_dict


__all__ = ("InfoMiddleware",)


class InfoMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path in ("/info", "/info/"):
            return JsonResponse(make_project_info_dict())
        return self.get_response(request)
