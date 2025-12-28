from typing import Callable

from celery import signals, Celery


__all__ = ("setup_telemetry", )


def setup_telemetry(app: Celery, init_function: Callable[[None], None]) -> None:
    app.conf.update(
        worker_hijack_root_logger=False,
    )
    signals.celeryd_init.connect(lambda **_: init_function(), weak=False)
