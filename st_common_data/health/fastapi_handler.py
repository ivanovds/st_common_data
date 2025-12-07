from functools import partial

from fastapi import FastAPI, Response
from fastapi import status
from fastapi.responses import JSONResponse

from .base import HealthHandler, HealthTypesType, HEALTH_STATUS


__all__ = ("implement_health_endpoint",)


def health_controller(
    health_handler: HealthHandler,
    type_: HealthTypesType,
    display: bool = False,
) -> Response:
    function = health_handler.get_method_by_type(type_)

    status_ = function()
    if status_["status"] == HEALTH_STATUS.UNHEALTHY.value:
        if display:
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=status_)
        else:
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    if display:
        return JSONResponse(status_code=status.HTTP_200_OK, content=status_)
    else:
        return Response(status_code=status.HTTP_200_OK)

    
def implement_health_endpoint(
    health_handler: HealthHandler,
    app: FastAPI,
) -> None:
    # Remove after migration to GCP
    app.get("/health/")(lambda: JSONResponse(status_code=status.HTTP_200_OK, content={"ok": True}))

    app.get("/health/{type_}/")(partial(health_controller, health_handler))


