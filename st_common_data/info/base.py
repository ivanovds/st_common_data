import logging
from typing import TypedDict

try:
    from app.settings import config
    VERSION = config.version
    PROJECT_NAME = config.project_name
    ENVIRONMENT = config.environment
except ImportError:
    from django.conf import settings
    VERSION = settings.VERSION
    PROJECT_NAME = settings.PROJECT_NAME
    ENVIRONMENT = settings.ENVIRONMENT


logger = logging.getLogger(__name__)


__all__ = ("ApplicationInfo", "make_project_info_dict", "make_user_agent",)


class ApplicationInfo(TypedDict):
    name: str
    version: str
    environment: str


def make_project_info_dict() -> ApplicationInfo:
    return {
        "name": PROJECT_NAME,
        "version": VERSION,
        "environment": ENVIRONMENT,
    }


def make_user_agent() -> str:
    info = make_project_info_dict()
    return f"{info['name']}/{info['version']} {info['environment']}"
