"""Тесты транзакций (nullable fund_id)."""


def test_create_transaction_with_fund(client, auth_headers):
    f = client.post("/funds", json={"name": "Тест", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    r = client.post("/transactions", json={
        "date": "2025-06-01T00:00:00", "amount": 5000, "type": "income", "fund_id": fid
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["fund_id"] == fid


def test_create_transaction_without_fund(client, auth_headers):
    """fund_id=None допускается (учёт по фондам выключен)."""
    r = client.post("/transactions", json={
        "date": "2025-06-01T00:00:00", "amount": 5000, "type": "income"
    }, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["fund_id"] is None


def test_create_transaction_invalid_fund(client, auth_headers):
    r = client.post("/transactions", json={
        "date": "2025-06-01T00:00:00", "amount": 5000, "type": "income", "fund_id": 9999
    }, headers=auth_headers)
    assert r.status_code == 404


def test_list_transactions_filter_fund(client, auth_headers):
    f1 = client.post("/funds", json={"name": "Фонд1", "type": "budget"}, headers=auth_headers)
    f2 = client.post("/funds", json={"name": "Фонд2", "type": "budget"}, headers=auth_headers)
    client.post("/transactions", json={
        "date": "2025-01-01T00:00:00", "amount": 100, "type": "income", "fund_id": f1.json()["id"]
    }, headers=auth_headers)
    client.post("/transactions", json={
        "date": "2025-01-01T00:00:00", "amount": 200, "type": "income", "fund_id": f2.json()["id"]
    }, headers=auth_headers)
    r = client.get(f"/transactions?fund_id={f1.json()['id']}", headers=auth_headers)
    assert len(r.json()) == 1
    assert r.json()[0]["amount"] == 100


def test_update_transaction(client, auth_headers):
    f = client.post("/funds", json={"name": "Тест", "type": "budget"}, headers=auth_headers)
    fid = f.json()["id"]
    t = client.post("/transactions", json={
        "date": "2025-06-01T00:00:00", "amount": 100, "type": "income", "fund_id": fid
    }, headers=auth_headers)
    tid = t.json()["id"]
    r = client.put(f"/transactions/{tid}", json={"amount": 500}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["amount"] == 500


def test_delete_transaction(client, auth_headers):
    t = client.post("/transactions", json={
        "date": "2025-06-01T00:00:00", "amount": 100, "type": "income"
    }, headers=auth_headers)
    tid = t.json()["id"]
    r = client.delete(f"/transactions/{tid}", headers=auth_headers)
    assert r.status_code == 204
