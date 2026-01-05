import time
import traceback
from typing import Callable, Any

from celery import shared_task, current_task
from celery import current_app as app
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
        # limits
        time_limit: int | None = None,
        soft_time_limit: int | None = None,
        # stroing result
        ignore_result: bool | None = None,
        store_errors_even_if_ignored: bool | None = None,
        # retring
        max_retries: int = 3,
        default_retry_delay: int = 60,  # minute
        retry_backoff: bool | int = False,
        retry_on_any_error: bool = False,
        autoretry_for_exception: tuple[Exception, ...] = tuple(),
    ) -> Callable:
        def wrapper(func):
            return shared_task(
                name=name,

                # to restart on celery shutdown
                acks_late=True,

                # to not pass None
                **({"on_failure": on_failure} if on_failure else {}),

                **({"time_limit": time_limit} if time_limit else {}),
                **({"soft_time_limit": soft_time_limit} if soft_time_limit else {}),
                
                **({"ignore_result": ignore_result} if ignore_result else {}),
                **({"store_errors_even_if_ignored": store_errors_even_if_ignored}
                   if store_errors_even_if_ignored
                   else {}),

                max_retries=max_retries,
                retry_backoff=retry_backoff,
                retry_jitter=False,
                default_retry_delay=default_retry_delay,
                autoretry_for=(
                    (*autoretry_for_exception, Exception)
                    if retry_on_any_error
                    else autoretry_for_exception
                ),
            )(func)

        return wrapper

    def get_current_step(
        self,
        step_mapper: Callable[..., Any] | None = None,
        default_step: Any = None,
    ) -> tuple[Any, JsonType | None]:
        task_id = current_task.request.id
        if not task_id:
            return default_step, None
        try:
            step = http_request(
                url=settings.CELERY_ADMIN_URL + f"tasks/steps/django/{task_id}/",
                method="GET",
                bearer=service_auth0_token,
                log_errors=False,
            )
        except HTTPError as e:
            if e.response.status_code != status_codes.not_found:
                logger.error(traceback.format_exception_only(e))

            return default_step, None

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
        if not task_id:
            return step, data

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

    def wait_until_all_tasks_are_finished(
        self,
        task_name: str | list,
        retry: int = 1,
    ) -> None:
        """Wait until all celery tasks with specified name or list of names are finished"""

        while True:
            if isinstance(task_name, str):
                if not self.check_if_task_is_running(task_name):
                    break
            elif isinstance(task_name, list):
                if all([not self.check_if_task_is_running(task) for task in task_name]):
                    break
            else:
                raise ValueError(f'Invalid task_name type: {type(task_name)}')
            time.sleep(10)

        if retry:
            self.wait_until_all_tasks_are_finished(task_name, retry - 1)

    def check_if_task_is_running(self, task_name: str) -> bool:
        inspector = app.control.inspect()

        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}

        for inspection_result in [active, scheduled, reserved]:
            for worker, tasks in inspection_result.items():
                for task in tasks:
                    current_task_name = task.get('name')

                    # scheduled and reserved tasks contains name in request
                    if not current_task_name:
                        request_info = task.get('request', {})
                        current_task_name = request_info.get('name')

                    if current_task_name == task_name:
                        return True
        return False
