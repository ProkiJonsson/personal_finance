"""Тесты фондов (6 типов)."""


def test_create_fund_budget(client, auth_headers):
    r = client.post("/funds", json={"name": "Текущие расходы", "type": "budget"}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "budget"
    assert data["balance"] == 0.0
    assert data["is_archived"] is False
    assert data["is_system"] is False


def test_create_fund_all_types(client, auth_headers):
    types = ["budget", "investment", "tax_reserve", "debt", "loan", "placement"]
    for t in types:
        r = client.post("/funds", json={"name": f"Фонд {t}", "type": t}, headers=auth_headers)
        assert r.status_code == 201, f"Failed for type {t}: {r.json()}"


def test_create_fund_with_contract(client, auth_headers):
    cp = client.post("/counterparties", json={"name": "ВТБ"}, headers=auth_headers)
    contract_id = cp.json()["contracts"][0]["id"]
    r = client.post("/funds", json={
        "name": "Вклад ВТБ", "type": "placement", "contract_id": contract_id
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["contract_id"] == contract_id
    assert r.json()["counterparty_name"] == "ВТБ"
    assert r.json()["contract_name"] == "Основной"


def test_create_fund_invalid_contract(client, auth_headers):
    r = client.post("/funds", json={
        "name": "Фонд", "type": "loan", "contract_id": 9999
    }, headers=auth_headers)
    assert r.status_code == 404


def test_list_funds_filter_type(client, auth_headers):
    client.post("/funds", json={"name": "Бюджет", "type": "budget"}, headers=auth_headers)
    client.post("/funds", json={"name": "Инвест", "type": "investment"}, headers=auth_headers)
    r = client.get("/funds?type=budget", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["type"] == "budget"


def test_list_funds_filter_archived(client, auth_headers):
    f = client.post("/funds", json={"name": "Фонд", "type": "loan"}, headers=auth_headers)
    fid = f.json()["id"]
    client.put(f"/funds/{fid}", json={"is_archived": True}, headers=auth_headers)
    r = client.get("/funds?archived=false", headers=auth_headers)
    assert len(r.json()) == 0
    r = client.get("/funds?archived=true", headers=auth_headers)
    assert len(r.json()) == 1


def test_update_fund(client, auth_headers):
    f = client.post("/funds", json={"name": "Старое", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    r = client.put(f"/funds/{fid}", json={"name": "Новое", "is_archived": True}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Новое"
    assert r.json()["is_archived"] is True


def test_delete_fund(client, auth_headers):
    f = client.post("/funds", json={"name": "Удаляемый", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    r = client.delete(f"/funds/{fid}", headers=auth_headers)
    assert r.status_code == 204


def test_delete_fund_with_transactions_fails(client, auth_headers):
    f = client.post("/funds", json={"name": "С операциями", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    client.post("/transactions", json={
        "date": "2025-01-01T00:00:00", "amount": 100, "type": "income", "fund_id": fid
    }, headers=auth_headers)
    r = client.delete(f"/funds/{fid}", headers=auth_headers)
    assert r.status_code == 409


def test_fund_balance_calculation(client, auth_headers):
    f = client.post("/funds", json={"name": "Баланс", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    client.post("/transactions", json={
        "date": "2025-01-01T00:00:00", "amount": 1000, "type": "income", "fund_id": fid
    }, headers=auth_headers)
    client.post("/transactions", json={
        "date": "2025-01-02T00:00:00", "amount": 300, "type": "expense", "fund_id": fid
    }, headers=auth_headers)
    r = client.get("/funds", headers=auth_headers)
    fund = [x for x in r.json() if x["id"] == fid][0]
    assert fund["balance"] == 700.0
