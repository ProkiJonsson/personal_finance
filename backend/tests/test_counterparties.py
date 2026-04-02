"""Тесты контрагентов и договоров."""
import models


def test_create_counterparty(client, auth_headers):
    r = client.post("/counterparties", json={
        "name": "ВТБ", "description": "Банк"
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "ВТБ"
    assert data["balance"] == 0.0
    # Автоматически создан договор "Основной"
    assert len(data["contracts"]) == 1
    assert data["contracts"][0]["name"] == "Основной"


def test_list_counterparties(client, auth_headers):
    client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    client.post("/counterparties", json={"name": "Т-Банк"}, headers=auth_headers)
    r = client.get("/counterparties", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_counterparty(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    r = client.get(f"/counterparties/{cp_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "ВТБ"


def test_update_counterparty(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    r = client.put(f"/counterparties/{cp_id}", json={"name": "ВТБ Банк"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "ВТБ Банк"


def test_delete_counterparty(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    r = client.delete(f"/counterparties/{cp_id}", headers=auth_headers)
    assert r.status_code == 204


def test_delete_counterparty_with_fund_fails(client, auth_headers, db, user):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    contract_id = cr.json()["contracts"][0]["id"]
    # Создаём фонд привязанный к договору
    client.post("/funds", json={
        "name": "Вклад ВТБ", "type": "placement", "contract_id": contract_id
    }, headers=auth_headers)
    r = client.delete(f"/counterparties/{cp_id}", headers=auth_headers)
    assert r.status_code == 409


def test_create_contract(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    r = client.post(f"/counterparties/{cp_id}/contracts", json={
        "name": "Вклад 12мес", "description": "до 31.12.2025"
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["name"] == "Вклад 12мес"


def test_list_contracts(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    client.post(f"/counterparties/{cp_id}/contracts", json={"name": "Вклад 6мес"}, headers=auth_headers)
    r = client.get(f"/counterparties/{cp_id}/contracts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2  # "Основной" + "Вклад 6мес"


def test_delete_default_contract_fails(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    contract_id = cr.json()["contracts"][0]["id"]
    r = client.delete(f"/counterparties/contracts/{contract_id}", headers=auth_headers)
    assert r.status_code == 409


def test_delete_contract_with_fund_fails(client, auth_headers):
    cr = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    cp_id = cr.json()["id"]
    c2 = client.post(f"/counterparties/{cp_id}/contracts", json={"name": "Вклад"}, headers=auth_headers)
    contract_id = c2.json()["id"]
    client.post("/funds", json={
        "name": "Вклад ВТБ", "type": "placement", "contract_id": contract_id
    }, headers=auth_headers)
    r = client.delete(f"/counterparties/contracts/{contract_id}", headers=auth_headers)
    assert r.status_code == 409
