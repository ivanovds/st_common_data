import logging
import os

__all__ = ("apply_semconv_opt_in",)

logger = logging.getLogger(__name__)


def apply_semconv_opt_in(opt_in: str | None = None) -> None:
    value = "http/dup" if opt_in is None else opt_in
    if not value:
        return

    applied = os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", value)
    logger.info("HTTP semconv opt-in: %s", applied)
