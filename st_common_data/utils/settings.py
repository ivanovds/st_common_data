try:
    from app.settings import config as settings
except ImportError:
    from django.conf import settings  # type: ignore


__all__ = ("get_settings",)


def get_settings():
    return settings
