from fastapi.testclient import TestClient


def test_health_checks_application_and_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "栗子杯 API",
        "database": "ok",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_unknown_route_uses_the_shared_error_shape(client: TestClient) -> None:
    response = client.get("/api/not-a-route", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 404
    assert response.json() == {
        "code": "NOT_FOUND",
        "message": "请求的资源不存在",
        "details": None,
        "request_id": "test-request",
    }

