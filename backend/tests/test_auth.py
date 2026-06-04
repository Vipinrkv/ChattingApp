def test_health_endpoint_is_available(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_requires_authorization(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
