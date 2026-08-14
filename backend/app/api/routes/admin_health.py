from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentPrincipal, require_roles
from app.auth.roles import Role

router = APIRouter()


@router.get("/health")
def admin_health(
    principal: Annotated[CurrentPrincipal, Depends(require_roles(Role.TOURNAMENT_ADMIN))],
) -> dict[str, str]:
    return {"status": "ok", "role": principal.role.value}

