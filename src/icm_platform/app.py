from fastapi import FastAPI

from icm_platform.db import init_db
from icm_platform.routes.auth import router as auth_router
from icm_platform.routes.workspace import router as workspace_router


def create_app() -> FastAPI:
    app = FastAPI(title="icm-platform")
    init_db()
    app.include_router(auth_router)
    app.include_router(workspace_router)
    return app


app = create_app()
