"""Тесты каскадов (расклад)."""


def _make_funds(client, auth_headers):
    """Создаёт набор фондов для каскада."""
    ids = {}
    for name, ftype in [
        ("Текущие расходы", "budget"),
        ("Я", "budget"),
        ("Резервный", "budget"),
        ("Фонд Инвестиций", "investment"),
    ]:
        r = client.post("/funds", json={"name": name, "type": ftype}, headers=auth_headers)
        ids[name] = r.json()["id"]
    return ids


def test_create_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    r = client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [
            {"fund_id": funds["Текущие расходы"], "target_amount": 205000, "sort_order": 0},
            {"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 1},
            {"fund_id": funds["Резервный"], "target_amount": 25000, "sort_order": 2},
        ],
        "split_rules": [
            {"trigger_position": 0, "target_fund_id": funds["Фонд Инвестиций"], "percentage": 0.10},
        ]
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert len(data["slots"]) == 3
    assert len(data["split_rules"]) == 1
    assert data["slots"][0]["fund_name"] == "Текущие расходы"


def test_get_active_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    # Создаём старый и новый каскад
    client.post("/cascades", json={
        "effective_from": "2024-01-01",
        "slots": [{"fund_id": funds["Текущие расходы"], "target_amount": 100000, "sort_order": 0}],
    }, headers=auth_headers)
    client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": funds["Текущие расходы"], "target_amount": 205000, "sort_order": 0}],
    }, headers=auth_headers)
    r = client.get("/cascades/active", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["slots"][0]["target_amount"] == 205000


def test_list_cascades(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    client.post("/cascades", json={
        "effective_from": "2024-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 0}],
    }, headers=auth_headers)
    client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 50000, "sort_order": 0}],
    }, headers=auth_headers)
    r = client.get("/cascades", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    cr = client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 0}],
    }, headers=auth_headers)
    cid = cr.json()["id"]
    r = client.put(f"/cascades/{cid}", json={
        "slots": [{"fund_id": funds["Я"], "target_amount": 50000, "sort_order": 0}],
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["slots"][0]["target_amount"] == 50000


def test_cannot_update_old_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    old = client.post("/cascades", json={
        "effective_from": "2024-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 0}],
    }, headers=auth_headers)
    client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 50000, "sort_order": 0}],
    }, headers=auth_headers)
    r = client.put(f"/cascades/{old.json()['id']}", json={
        "slots": [{"fund_id": funds["Я"], "target_amount": 99999, "sort_order": 0}],
    }, headers=auth_headers)
    assert r.status_code == 409


def test_delete_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    cr = client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 0}],
    }, headers=auth_headers)
    r = client.delete(f"/cascades/{cr.json()['id']}", headers=auth_headers)
    assert r.status_code == 204


def test_copy_cascade(client, auth_headers):
    funds = _make_funds(client, auth_headers)
    cr = client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [
            {"fund_id": funds["Текущие расходы"], "target_amount": 205000, "sort_order": 0},
            {"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 1},
        ],
        "split_rules": [
            {"trigger_position": 0, "target_fund_id": funds["Фонд Инвестиций"], "percentage": 0.10},
        ]
    }, headers=auth_headers)
    cid = cr.json()["id"]
    r = client.post(f"/cascades/{cid}/copy?effective_from=2026-01-01", headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["effective_from"] == "2026-01-01"
    assert len(data["slots"]) == 2
    assert len(data["split_rules"]) == 1


def test_create_cascade_invalid_fund(client, auth_headers):
    r = client.post("/cascades", json={
        "effective_from": "2025-01-01",
        "slots": [{"fund_id": 9999, "target_amount": 100000, "sort_order": 0}],
    }, headers=auth_headers)
    assert r.status_code == 404
