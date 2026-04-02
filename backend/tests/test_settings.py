"""Тесты настроек (AppSetting + НДФЛ)."""


def test_get_default_settings(client, auth_headers):
    r = client.get("/settings", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["fund_accounting_enabled"] is False
    assert data["max_attachment_size_mb"] == 10


def test_update_settings(client, auth_headers):
    r = client.put("/settings", json={
        "fund_accounting_enabled": True,
        "max_attachment_size_mb": 20,
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["fund_accounting_enabled"] is True
    assert r.json()["max_attachment_size_mb"] == 20


def test_create_tax_setting(client, auth_headers):
    r = client.post("/settings/tax", json={
        "year": 2025,
        "tax_free_threshold": 160000,
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["year"] == 2025
    assert data["tax_free_threshold"] == 160000
    assert data["rate_standard"] == 0.13
    assert data["rate_elevated"] == 0.15
    assert data["elevated_threshold"] == 2000000


def test_upsert_tax_setting(client, auth_headers):
    client.post("/settings/tax", json={
        "year": 2025, "tax_free_threshold": 160000,
    }, headers=auth_headers)
    r = client.post("/settings/tax", json={
        "year": 2025, "tax_free_threshold": 180000,
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["tax_free_threshold"] == 180000
    # Убедимся что не дублируется
    r = client.get("/settings/tax", headers=auth_headers)
    assert len(r.json()) == 1


def test_list_tax_settings(client, auth_headers):
    client.post("/settings/tax", json={"year": 2024, "tax_free_threshold": 150000}, headers=auth_headers)
    client.post("/settings/tax", json={"year": 2025, "tax_free_threshold": 160000}, headers=auth_headers)
    r = client.get("/settings/tax", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["year"] == 2025  # DESC


def test_delete_tax_setting(client, auth_headers):
    client.post("/settings/tax", json={"year": 2025, "tax_free_threshold": 160000}, headers=auth_headers)
    r = client.delete("/settings/tax/2025", headers=auth_headers)
    assert r.status_code == 204
    r = client.get("/settings/tax", headers=auth_headers)
    assert len(r.json()) == 0


def test_delete_nonexistent_tax(client, auth_headers):
    r = client.delete("/settings/tax/2099", headers=auth_headers)
    assert r.status_code == 404
