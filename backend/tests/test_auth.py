"""Тесты авторизации и регистрации."""


def test_register(client):
    r = client.post("/auth/register", json={
        "name": "Иван", "email": "ivan@test.com", "password": "secret123"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Иван"
    assert data["email"] == "ivan@test.com"


def test_register_duplicate_email(client, user):
    r = client.post("/auth/register", json={
        "name": "Дубль", "email": user.email, "password": "secret123"
    })
    assert r.status_code == 409


def test_login(client, user):
    r = client.post("/auth/login", json={
        "email": user.email, "password": "password123"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client, user):
    r = client.post("/auth/login", json={
        "email": user.email, "password": "wrong"
    })
    assert r.status_code == 401


def test_unauthorized_access(client):
    r = client.get("/funds")
    assert r.status_code == 401
