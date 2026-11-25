import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_items.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_crud_items_lifecycle(client):
    empty_res = client.get("/api/items")
    assert empty_res.status_code == 200
    assert empty_res.json()["items"] == []

    create_res = client.post(
        "/api/items",
        json={"title": "Deploy EC2", "description": "Verificar contenedores", "status": "pending"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["title"] == "Deploy EC2"
    item_id = created["id"]

    list_res = client.get("/api/items")
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) == 1

    del_res = client.delete(f"/api/items/{item_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    not_found_res = client.delete(f"/api/items/{item_id}")
    assert not_found_res.status_code == 404


def test_create_item_validation_error(client):
    res = client.post("/api/items", json={"title": "", "status": "invalid"})
    assert res.status_code == 422


def test_simulate_error_endpoint(client):
    res = client.get("/api/simulate-error")
    assert res.status_code == 500
    assert "detail" in res.json()
