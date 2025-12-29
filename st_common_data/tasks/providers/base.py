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
        on_failuer,
        time_limit,
        soft_time_limit,
        ignore_result,
        store_errors_even_if_ignored,
    ):
        pass

