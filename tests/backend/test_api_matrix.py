import pytest
from fastapi.testclient import TestClient

from backend.app import database
from backend.app.main import app, create_access_token, decode_access_token


@pytest.fixture(scope="module")
def shared_client(tmp_path_factory, monkeypatch_module=None):
    db_dir = tmp_path_factory.mktemp("matrix_db")
    db_file = db_dir / "matrix_app.db"
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_PATH", str(db_file))
    mp.setenv("DEFAULT_ADMIN_USER", "admin")
    mp.setenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    with TestClient(app) as client:
        yield client
    mp.undo()


@pytest.fixture(scope="module")
def admin_headers(shared_client: TestClient):
    res = shared_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# 1) 200 pruebas unitarias de hash y verificación de contraseñas
PASSWORD_CASES = [
    (f"Pass_{i}!abc", f"Pass_{i}!abc", True) for i in range(100)
] + [
    (f"Pass_{i}!abc", f"Wrong_{i}!xyz", False) for i in range(100)
]


@pytest.mark.parametrize("raw_pw,candidate_pw,expected", PASSWORD_CASES)
def test_hash_and_verify_password_matrix(raw_pw, candidate_pw, expected):
    hashed = database.hash_password(raw_pw)
    assert "$" in hashed
    assert database.verify_password(candidate_pw, hashed) is expected


# 2) 100 pruebas unitarias de generación y decodificación de tokens HMAC
TOKEN_CASES = [
    (i + 1, f"user_{i}", ["admin", "user", "viewer"][i % 3]) for i in range(100)
]


@pytest.mark.parametrize("uid,uname,role", TOKEN_CASES)
def test_token_create_and_decode_matrix(uid, uname, role):
    token = create_access_token({"id": uid, "username": uname, "role": role})
    payload = decode_access_token(token)
    assert payload["sub"] == uid
    assert payload["username"] == uname
    assert payload["role"] == role


# 3) 150 pruebas de endpoint POST /api/auth/login
LOGIN_CASES = (
    [({"username": "admin", "password": "admin123"}, 200) for _ in range(30)]
    + [({"username": "admin", "password": f"bad_pass_{i}"}, 401) for i in range(60)]
    + [({"username": f"unknown_{i}", "password": "admin123"}, 401) for i in range(40)]
    + [({"username": "", "password": "admin123"}, 422) for _ in range(10)]
    + [({"username": "admin", "password": ""}, 422) for _ in range(10)]
)


@pytest.mark.parametrize("payload,expected_status", LOGIN_CASES)
def test_login_matrix(shared_client: TestClient, payload, expected_status):
    res = shared_client.post("/api/auth/login", json=payload)
    assert res.status_code == expected_status


# 4) 200 pruebas de creación y validación en POST /api/users
CREATE_VALID_CASES = [
    (
        {
            "username": f"mat_user_{i}",
            "email": f"mat_user_{i}@proyecto2.local",
            "full_name": f"Usuario Matriz {i}",
            "role": ["user", "admin", "viewer"][i % 3],
            "password": f"Clave_{i}_ok",
        },
        201,
    )
    for i in range(100)
]

CREATE_INVALID_CASES = (
    [
        (
            {
                "username": "ab",
                "email": f"inv1_{i}@test.com",
                "full_name": "Nombre Valido",
                "role": "user",
                "password": "password123",
            },
            422,
        )
        for i in range(25)
    ]
    + [
        (
            {
                "username": f"inv_email_{i}",
                "email": "a@b",
                "full_name": "Nombre Valido",
                "role": "user",
                "password": "password123",
            },
            422,
        )
        for i in range(25)
    ]
    + [
        (
            {
                "username": f"inv_role_{i}",
                "email": f"inv_role_{i}@test.com",
                "full_name": "Nombre Valido",
                "role": f"superrole_{i}",
                "password": "password123",
            },
            422,
        )
        for i in range(25)
    ]
    + [
        (
            {
                "username": f"inv_pw_{i}",
                "email": f"inv_pw_{i}@test.com",
                "full_name": "Nombre Valido",
                "role": "user",
                "password": "123",
            },
            422,
        )
        for i in range(25)
    ]
)


@pytest.mark.parametrize("payload,expected_status", CREATE_VALID_CASES + CREATE_INVALID_CASES)
def test_create_user_validation_matrix(shared_client: TestClient, admin_headers, payload, expected_status):
    res = shared_client.post("/api/users", headers=admin_headers, json=payload)
    assert res.status_code == expected_status


# 5) 150 pruebas de actualización en PUT /api/users/{id}
UPDATE_VALID_CASES = [
    (
        i + 2,  # IDs creados en el bloque anterior (1 es admin)
        {"full_name": f"Editado {i}", "role": ["viewer", "user", "admin"][i % 3]},
        200,
    )
    for i in range(90)
]
UPDATE_NOT_FOUND_CASES = [
    (90000 + i, {"full_name": f"NoExiste {i}"}, 404) for i in range(30)
]
UPDATE_INVALID_CASES = [
    (2, {"role": f"bad_role_{i}"}, 422) for i in range(30)
]


@pytest.mark.parametrize("user_id,payload,expected_status", UPDATE_VALID_CASES + UPDATE_NOT_FOUND_CASES + UPDATE_INVALID_CASES)
def test_update_user_matrix(shared_client: TestClient, admin_headers, user_id, payload, expected_status):
    res = shared_client.put(f"/api/users/{user_id}", headers=admin_headers, json=payload)
    assert res.status_code == expected_status


# 6) 100 pruebas de rechazo de autorización en rutas protegidas
AUTH_REJECT_CASES = (
    [("/api/users", None) for _ in range(25)]
    + [("/api/auth/me", None) for _ in range(25)]
    + [("/api/users", {"Authorization": f"Bearer token_invalido_{i}"}) for i in range(25)]
    + [("/api/auth/me", {"Authorization": f"Basic fake_{i}"}) for i in range(25)]
)


@pytest.mark.parametrize("path,headers", AUTH_REJECT_CASES)
def test_auth_header_rejection_matrix(shared_client: TestClient, path, headers):
    res = shared_client.get(path, headers=headers)
    assert res.status_code == 401
