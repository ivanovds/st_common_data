import base64
from typing import Callable, Any

from celery import shared_task, current_task
from django.conf import settings
from requests.exceptions import HTTPError
from requests import codes as status_codes

from st_common_data.auth.django_auth import service_auth0_token
from st_common_data.utils.typing import JsonType
from st_common_data.utils.common import http_request
from .base import AbstractProvider


__all__ = ("CeleryProvider",)


class CeleryProvider(AbstractProvider):
    def run_task(
        self,
        task: Callable[[JsonType], Any],
        args: list[JsonType] = [],
        kwargs: dict[str, JsonType] = {},
    ) -> None:
        task.delay(*args, **kwargs)

    def declare_task(
        self,
        *,
        name: str,
        on_failure: Callable[..., Any] | None = None,
        time_limit: int | None = None,
        soft_time_limit: int | None = None,
        ignore_result: bool | None = None,
        store_errors_even_if_ignored: bool | None = None,
    ) -> Callable:
        def wrapper(func):
            return shared_task(
                name=name,
                acks_late=True,
                on_failure=on_failure,
                time_limit=time_limit,
                soft_time_limit=soft_time_limit,
                ignore_result=ignore_result,
                store_errors_even_if_ignored=store_errors_even_if_ignored,
            )(func)

        return wrapper

    def get_current_step(
        self,
        step_mapper: Callable[..., Any] | None = None,
        default_step: Any = None,
    ) -> tuple[Any, JsonType | None]:
        task_id = current_task.request.id
        try:
            step = http_request(
                url=settings.CELERY_ADMIN_URL + f"tasks/steps/django/{task_id}/",
                method="GET",
                bearer=service_auth0_token,
                log_errors=False,
            )
        except HTTPError as e:
            if e.response.status_code == status_codes.not_found:
                return default_step, None
            else:
                raise e

        step_ = step["step"]
        if step_mapper:
            step_ = step_mapper(step_)

        return step_, step["data"]

    def set_current_step(
        self,
        *,
        step: str,
        data: JsonType | None = None,
    ) -> tuple[Any, JsonType | None]:
        task_id = current_task.request.id
        body = {
            "step": str(step),
            "data": data,
        }

        http_request(
            url=settings.CELERY_ADMIN_URL + f"tasks/steps/django/{task_id}/",
            method="POST",
            data=body,
            bearer=service_auth0_token,
        )
        return step, data
