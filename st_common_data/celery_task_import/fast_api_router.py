from fastapi import BackgroundTasks, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter

from st_common_data.auth.fastapi_auth import get_current_service
from st_common_data.celery_task_import.handlers import CeleryTaskFormator
from ..dependencies import get_db
from ..models import UserDataModel
from .settings import config

router = APIRouter(
    prefix='/api/import_tasks',
)


@router.get("/")
async def root(
    *,
    session: Session = Depends(get_db),
    user: UserDataModel = Depends(get_current_service),
):
    handler = CeleryTaskFormator(config.task_default_queue)
    handler.run()
    return handler.result
