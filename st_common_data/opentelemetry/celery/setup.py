from typing import Callable

from celery import signals, Celery


__all__ = ("setup_telemetry", )


def setup_telemetry(app: Celery, init_function: Callable[[None], None]) -> None:
    app.conf.update(
        worker_hijack_root_logger=False,
    )
    # worker_process_init is crucial: it runs AFTER the process forks.
    # OpenTelemetry uses background threads for exporting metrics. If initialized before fork,
    # those threads don't survive in the child processes and no metrics will be sent.
    signals.worker_process_init.connect(lambda **_: init_function(), weak=False)
