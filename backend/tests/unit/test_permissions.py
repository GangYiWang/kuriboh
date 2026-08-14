import pytest

from app.auth.dependencies import CurrentPrincipal, require_roles
from app.auth.roles import Role
from app.core.errors import AppError


def test_admin_role_passes_admin_boundary() -> None:
    checker = require_roles(Role.TOURNAMENT_ADMIN)
    principal = CurrentPrincipal(user_id="admin-1", role=Role.TOURNAMENT_ADMIN)

    assert checker(principal) == principal


def test_player_role_is_rejected_by_admin_boundary() -> None:
    checker = require_roles(Role.TOURNAMENT_ADMIN)
    principal = CurrentPrincipal(user_id="player-1", role=Role.PLAYER)

    with pytest.raises(AppError) as caught:
        checker(principal)

    assert caught.value.status_code == 403
    assert caught.value.code == "FORBIDDEN"

