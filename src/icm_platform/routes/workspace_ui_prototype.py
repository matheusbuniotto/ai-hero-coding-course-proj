"""PROTOTYPE — throwaway. Three variants of the workspace UI on one route.

Question: what should the main workspace surface look like (tree + agent session +
propose/approve) for issue #1?

Serves /prototype/workspace-ui?variant=A|B|C. Mock data only, no auth, no DB — the
question is "what should this look like", not "does the backend work". Delete this
file (and its template) once a variant wins.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from icm_platform.paths import TEMPLATES_DIR

router = APIRouter(prefix="/prototype", tags=["prototype"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/workspace-ui", response_class=HTMLResponse)
def workspace_ui_prototype(request: Request, variant: str = "A") -> HTMLResponse:
    return templates.TemplateResponse(
        request, "workspace_ui_prototype.html", {"variant": variant.upper()}
    )
