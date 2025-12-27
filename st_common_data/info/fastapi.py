from fastapi import FastAPI
from fastapi import status
from fastapi.responses import JSONResponse

from .base import make_project_info_dict


__all__ = ("implement_info_endpoint",)


def info_controller() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=make_project_info_dict(),
    )

    
def implement_info_endpoint(
    app: FastAPI,
) -> None:
    app.get("/info/")(info_controller)

