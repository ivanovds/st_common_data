import logging
from typing import TypedDict

from st_common_data.utils.settings import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


__all__ = ("ApplicationInfo", "make_project_info_dict", "make_user_agent",)


try:
    VERSION = settings.version
    PROJECT_NAME = settings.project_name
    ENVIRONMENT = settings.environment
except AttributeError:
    VERSION = settings.VERSION
    PROJECT_NAME = settings.PROJECT_NAME
    ENVIRONMENT = settings.ENVIRONMENT


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
