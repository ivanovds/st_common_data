from fastapi import BackgroundTasks, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import APIRouter

from st_common_data.celery_task_import.handlers import CeleryTaskFormator
from app.settings import config


router = APIRouter(
    prefix='/api/import_tasks',
)


@router.get("/")
async def root(
):
    handler = CeleryTaskFormator(config.celery_task_default_queue)
    handler.run()
    return handler.result
