from fastapi.testclient import TestClient

from dummy_app.main import app

client = TestClient(app)


def test_get_profile_returns_200_with_auth():
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "user-001"
    assert body["email"] == "demo@example.com"
    assert body["displayName"] == "Demo User"


def test_get_profile_returns_401_without_auth():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_profile_returns_404_for_not_found_user():
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-found-user"}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "user_not_found"
