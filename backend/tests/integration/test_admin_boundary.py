from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.auth.roles import Role
from app.main import app


def test_admin_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/admin/health")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_player_cannot_access_admin_endpoint(client: TestClient) -> None:
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        user_id="player-1",
        role=Role.PLAYER,
    )

    response = client.get("/api/admin/health")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_can_pass_the_role_boundary(client: TestClient) -> None:
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        user_id="admin-1",
        role=Role.TOURNAMENT_ADMIN,
    )

    response = client.get("/api/admin/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "role": "TOURNAMENT_ADMIN"}
