"""Тесты админ-панели (page content, admin settings, доступ)."""
import models
from auth import create_access_token, hash_password


def _create_admin(db) -> tuple:
    """Создаёт админ-пользователя и возвращает (user, headers)."""
    u = models.User(
        name="Admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        is_admin=True,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(u.id, u.name, is_admin=True, is_active=True)
    return u, {"Authorization": f"Bearer {token}"}


# ── Page Content ──

def test_get_page_content_public(client):
    """GET /admin/page-content доступен без авторизации."""
    r = client.get("/admin/page-content")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_put_page_content_forbidden(client, auth_headers):
    """Не-админ не может обновлять контент страниц."""
    r = client.put("/admin/page-content", json={
        "page_key": "dashboard",
        "items": [{"element_key": "header", "content": "Тест"}],
    }, headers=auth_headers)
    assert r.status_code == 403


def test_put_page_content_admin(client, db):
    """Админ может обновлять контент страниц."""
    _, admin_headers = _create_admin(db)
    r = client.put("/admin/page-content", json={
        "page_key": "dashboard",
        "items": [
            {"element_key": "header", "content": "Новый заголовок"},
            {"element_key": "tab_title", "content": "Новый title"},
        ],
    }, headers=admin_headers)
    assert r.status_code == 200

    # Проверяем что контент обновился
    r = client.get("/admin/page-content")
    data = r.json()
    assert data["dashboard"]["header"] == "Новый заголовок"
    assert data["dashboard"]["tab_title"] == "Новый title"


# ── Admin Settings ──

def test_get_admin_settings(client, auth_headers):
    """Любой авторизованный пользователь может читать глобальные настройки."""
    r = client.get("/admin/settings", headers=auth_headers)
    assert r.status_code == 200
    assert "max_attachment_size_mb" in r.json()


def test_put_admin_settings_forbidden(client, auth_headers):
    """Не-админ не может обновлять глобальные настройки."""
    r = client.put("/admin/settings", json={
        "max_attachment_size_mb": 20,
    }, headers=auth_headers)
    assert r.status_code == 403


def test_put_admin_settings_admin(client, db):
    """Админ может обновлять глобальные настройки."""
    _, admin_headers = _create_admin(db)

    # Создаём дефолтную настройку
    db.add(models.AdminSetting(key="max_attachment_size_mb", value="10"))
    db.commit()

    r = client.put("/admin/settings", json={
        "max_attachment_size_mb": 25,
    }, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["max_attachment_size_mb"] == 25

    # Проверяем что значение сохранилось
    r = client.get("/admin/settings", headers=admin_headers)
    assert r.json()["max_attachment_size_mb"] == 25


# ── Image Upload ──

def test_upload_image_forbidden(client, auth_headers):
    """Не-админ не может загружать картинки."""
    r = client.post("/admin/upload-image", headers=auth_headers,
                    files={"file": ("test.png", b"\x89PNG\r\n", "image/png")})
    assert r.status_code == 403


def test_upload_image_admin(client, db):
    """Админ может загружать картинки."""
    _, admin_headers = _create_admin(db)
    # Минимальный PNG
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = client.post("/admin/upload-image",
                    headers={"Authorization": admin_headers["Authorization"]},
                    files={"file": ("test.png", png_data, "image/png")})
    assert r.status_code == 201
    data = r.json()
    assert data["url"].startswith("/admin/images/")


def test_upload_image_invalid_type(client, db):
    """Нельзя загружать файлы не-картинки."""
    _, admin_headers = _create_admin(db)
    r = client.post("/admin/upload-image",
                    headers={"Authorization": admin_headers["Authorization"]},
                    files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 400


# ── Users ──

def test_list_users(client, db):
    """Админ может видеть список пользователей."""
    _, admin_headers = _create_admin(db)
    r = client.get("/admin/users", headers=admin_headers)
    assert r.status_code == 200
    users = r.json()
    assert len(users) >= 1
    assert any(u["email"] == "admin@example.com" for u in users)


def test_list_users_forbidden(client, auth_headers):
    """Не-админ не может видеть список пользователей."""
    r = client.get("/admin/users", headers=auth_headers)
    assert r.status_code == 403


def test_search_users(client, db):
    """Поиск пользователей по имени и email."""
    _, admin_headers = _create_admin(db)
    # Создадим ещё пользователя
    u2 = models.User(name="Иван", email="ivan@test.com", password_hash=hash_password("123456"))
    db.add(u2)
    db.commit()

    r = client.get("/admin/users?search=ivan", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["email"] == "ivan@test.com"

    r = client.get("/admin/users?search=Иван", headers=admin_headers)
    assert len(r.json()) == 1


def test_toggle_admin(client, db):
    """Админ может назначить/снять права другому пользователю."""
    _, admin_headers = _create_admin(db)
    user = models.User(name="User", email="user2@test.com", password_hash=hash_password("123456"))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Назначить админом
    r = client.put(f"/admin/users/{user.id}", json={"is_admin": True}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_admin"] is True

    # Снять права
    r = client.put(f"/admin/users/{user.id}", json={"is_admin": False}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_admin"] is False


def test_cannot_remove_own_admin(client, db):
    """Админ не может снять права у самого себя."""
    admin_user, admin_headers = _create_admin(db)
    r = client.put(f"/admin/users/{admin_user.id}", json={"is_admin": False}, headers=admin_headers)
    assert r.status_code == 400


# ── Auth ──

def test_admin_flag_in_jwt(client, db):
    """is_admin передаётся в JWT при логине."""
    admin = models.User(
        name="Admin",
        email="admin2@example.com",
        password_hash=hash_password("admin123"),
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    r = client.post("/auth/login", json={
        "email": "admin2@example.com",
        "password": "admin123",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]

    import base64, json
    payload_b64 = token.split('.')[1]
    payload_b64 += '==' [:((4 - len(payload_b64) % 4) % 4)]
    payload = json.loads(base64.b64decode(payload_b64))
    assert payload["is_admin"] is True
    assert payload["is_active"] is True


def test_regular_user_no_admin(client, db):
    """Обычный пользователь не имеет is_admin в JWT."""
    user = models.User(
        name="User",
        email="user@example.com",
        password_hash=hash_password("user123"),
        is_active=True,
    )
    db.add(user)
    db.commit()

    r = client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "user123",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]

    import base64, json
    payload_b64 = token.split('.')[1]
    payload_b64 += '==' [:((4 - len(payload_b64) % 4) % 4)]
    payload = json.loads(base64.b64decode(payload_b64))
    assert payload["is_admin"] is False


# ── is_active ──

def test_inactive_user_gets_403(client, db):
    """Неактивный пользователь получает 403 на защищённые эндпоинты."""
    user = models.User(
        name="Inactive",
        email="inactive@test.com",
        password_hash=hash_password("123456"),
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.name, is_active=False)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/settings", headers=headers)
    assert r.status_code == 403
    assert "активации" in r.json()["detail"]


def test_toggle_active(client, db):
    """Админ может активировать пользователя."""
    _, admin_headers = _create_admin(db)
    user = models.User(name="New", email="new@test.com", password_hash=hash_password("123456"))
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.is_active is False

    r = client.put(f"/admin/users/{user.id}", json={"is_active": True}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is True


def test_cannot_deactivate_self(client, db):
    """Админ не может деактивировать самого себя."""
    admin_user, admin_headers = _create_admin(db)
    r = client.put(f"/admin/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 400


def test_new_user_inactive_by_default(client):
    """Новый зарегистрированный пользователь неактивен."""
    r = client.post("/auth/register", json={
        "name": "NewUser", "email": "newreg@test.com", "password": "123456",
    })
    assert r.status_code == 201
    token = r.json()["access_token"]

    import base64, json
    payload_b64 = token.split('.')[1]
    payload_b64 += '==' [:((4 - len(payload_b64) % 4) % 4)]
    payload = json.loads(base64.b64decode(payload_b64))
    assert payload["is_active"] is False
