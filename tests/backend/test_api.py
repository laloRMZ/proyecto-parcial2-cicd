import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_app.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setenv("DEFAULT_ADMIN_USER", "admin")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    with TestClient(app) as test_client:
        yield test_client


def _auth_headers(client: TestClient, username: str = "admin", password: str = "admin123"):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_login_success_and_failure(client):
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert good.status_code == 200
    data = good.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"


def test_users_require_authentication(client):
    res = client.get("/api/users")
    assert res.status_code == 401


def test_crud_users_lifecycle(client):
    headers = _auth_headers(client)

    list_initial = client.get("/api/users", headers=headers)
    assert list_initial.status_code == 200
    assert any(u["username"] == "admin" for u in list_initial.json()["users"])

    create_res = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "jdoe",
            "email": "jdoe@proyecto2.local",
            "full_name": "Juan Pérez",
            "role": "user",
            "password": "secret123",
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    user_id = created["id"]
    assert created["username"] == "jdoe"

    dup_res = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "jdoe",
            "email": "jdoe2@proyecto2.local",
            "full_name": "Otro",
            "role": "user",
            "password": "secret123",
        },
    )
    assert dup_res.status_code == 409

    upd_res = client.put(
        f"/api/users/{user_id}",
        headers=headers,
        json={"full_name": "Juan Pérez Actualizado", "role": "viewer"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["full_name"] == "Juan Pérez Actualizado"
    assert upd_res.json()["role"] == "viewer"

    new_login = client.post("/api/auth/login", json={"username": "jdoe", "password": "secret123"})
    assert new_login.status_code == 200

    del_res = client.delete(f"/api/users/{user_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    not_found = client.delete(f"/api/users/{user_id}", headers=headers)
    assert not_found.status_code == 404


def test_simulate_error_endpoint(client):
    res = client.get("/api/simulate-error")
    assert res.status_code == 500
    assert "detail" in res.json()
