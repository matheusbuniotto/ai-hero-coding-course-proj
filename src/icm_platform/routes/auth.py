from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from icm_platform.auth.service import SESSION_TTL, AuthService
from icm_platform.deps import (
    SESSION_COOKIE,
    dev_auth_enabled,
    get_auth_service,
    get_workspace_service,
    require_dev_auth,
)
from icm_platform.models import User
from icm_platform.paths import TEMPLATES_DIR
from icm_platform.workspace.service import WorkspaceService

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)

WORKSPACE_APP_URL = "/"
"""Where a fresh session lands: the workspace UI, which the dev server serves at the root."""


def _signed_in(
    user: User, session_token: str, workspace_service: WorkspaceService
) -> RedirectResponse:
    workspace_service.ensure_personal_workspace(user)
    response = RedirectResponse(url=WORKSPACE_APP_URL, status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "login.html", {"sent": False, "dev_auth": dev_auth_enabled()}
    )


@router.post("/magic-link", response_class=HTMLResponse)
def request_magic_link(
    request: Request,
    email: Annotated[str, Form()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> HTMLResponse:
    verify_url = str(request.url_for("verify_magic_link"))
    auth_service.request_magic_link(email, verify_url)
    return templates.TemplateResponse(
        request, "login.html", {"sent": True, "dev_auth": dev_auth_enabled()}
    )


@router.get("/verify")
def verify_magic_link(
    token: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> RedirectResponse:
    result = auth_service.verify_magic_link(token)
    if result is None:
        return RedirectResponse(url="/auth/login?error=invalid_or_expired", status_code=303)

    user, session_token = result
    return _signed_in(user, session_token, workspace_service)


@router.post("/dev-login", dependencies=[Depends(require_dev_auth)])
def dev_login(
    email: Annotated[str, Form()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> RedirectResponse:
    """Dev-only: sign in as `email` immediately, no magic link. 404s unless `ICM_DEV_AUTH=1`."""
    user, session_token = auth_service.dev_login(email)
    return _signed_in(user, session_token, workspace_service)


@router.post("/logout")
def logout(
    request: Request, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        auth_service.logout(token)
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
