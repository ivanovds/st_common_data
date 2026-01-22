from fastapi import BackgroundTasks, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter

from st_common_data.auth.fastapi_auth import get_current_service
from st_common_data.celery_task_import.handlers import CeleryTaskFormator
from app.dependencies import get_db
from app.models import UserDataModel
from app.settings import config

router = APIRouter(
    prefix='/api/import_tasks',
)


@router.get("/")
async def root(
    *,
    session: Session = Depends(get_db),
    user: UserDataModel = Depends(get_current_service),
):
    handler = CeleryTaskFormator(config.celery_task_default_queue)
    handler.run()
    return handler.result
