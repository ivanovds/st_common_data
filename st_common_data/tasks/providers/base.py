from abc import ABC, abstractmethod
from typing import Callable, Any

from st_common_data.utils.typing import JsonType


__all__ = ("AbstractProvider",)


class AbstractProvider(ABC):
    @abstractmethod
    def run_task(
        self,
        task: Callable[[JsonType], Any],
        args: list[JsonType],
        kwargs: dict[str, JsonType],
    ) -> None:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_current_step(
        self,
        step_mapper: Callable[..., Any] | None = None,
        default_step: Any = None,
    ) -> tuple[Any, JsonType | None]:
        pass

    @abstractmethod
    def set_current_step(
        self,
        *,
        step: str,
        data: JsonType | None = None,
    ) -> tuple[Any, JsonType | None]:
        pass

    @abstractmethod
    def wait_until_all_tasks_are_finished(
        self,
        task_name: str | list,
        retry: int = 1,
    ) -> None:
        pass

    @abstractmethod
    def check_if_task_is_running(self, task_name: str) -> bool:
        pass
