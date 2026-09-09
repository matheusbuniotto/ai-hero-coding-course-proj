from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from icm_platform.db import init_db
from icm_platform.routes.agent import router as agent_router
from icm_platform.routes.auth import router as auth_router
from icm_platform.routes.workspace import router as workspace_router
from icm_platform.routes.workspaces import router as workspaces_router
from icm_platform.workspace.service import WorkspaceAccessError


def create_app() -> FastAPI:
    app = FastAPI(title="icm-platform")
    init_db()
    app.include_router(auth_router)
    app.include_router(workspace_router)
    app.include_router(workspaces_router)
    app.include_router(agent_router)

    @app.exception_handler(WorkspaceAccessError)
    def handle_access_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    return app


app = create_app()
