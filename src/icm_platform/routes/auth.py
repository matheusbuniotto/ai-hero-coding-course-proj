from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from icm_platform.auth.service import SESSION_TTL, AuthService
from icm_platform.deps import SESSION_COOKIE, get_auth_service, get_workspace_service
from icm_platform.paths import TEMPLATES_DIR
from icm_platform.workspace.service import WorkspaceService

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"sent": False})


@router.post("/magic-link", response_class=HTMLResponse)
def request_magic_link(
    request: Request,
    email: Annotated[str, Form()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> HTMLResponse:
    verify_url = str(request.url_for("verify_magic_link"))
    auth_service.request_magic_link(email, verify_url)
    return templates.TemplateResponse(request, "login.html", {"sent": True})


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
    workspace_service.ensure_personal_workspace(user)
    response = RedirectResponse(url="/workspace", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
    )
    return response


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
