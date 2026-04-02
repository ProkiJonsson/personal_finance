"""Тесты распределения дохода (POST /funds/distribute)."""


def _setup_cascade(client, auth_headers):
    """Создаёт фонды + каскад для тестов distribute."""
    funds = {}
    for name, ftype in [
        ("Текущие расходы", "budget"),
        ("Я", "budget"),
        ("Резервный", "budget"),
        ("Фонд Инвестиций", "investment"),
    ]:
        r = client.post("/funds", json={"name": name, "type": ftype}, headers=auth_headers)
        funds[name] = r.json()["id"]

    client.post("/cascades", json={
        "effective_from": "2024-01-01",
        "slots": [
            {"fund_id": funds["Текущие расходы"], "target_amount": 205000, "sort_order": 0},
            {"fund_id": funds["Я"], "target_amount": 30000, "sort_order": 1},
            {"fund_id": funds["Резервный"], "target_amount": 25000, "sort_order": 2},
        ],
        "split_rules": [
            {"trigger_position": 0, "target_fund_id": funds["Фонд Инвестиций"], "percentage": 0.10},
            {"trigger_position": -1, "target_fund_id": funds["Фонд Инвестиций"], "percentage": 0.90},
        ]
    }, headers=auth_headers)
    return funds


def test_distribute_basic(client, auth_headers):
    """Доход меньше первого фонда — всё в Текущие расходы."""
    _setup_cascade(client, auth_headers)
    r = client.post("/funds/distribute", json={
        "amount": 100000,
    }, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_distributed"] == 100000
    assert data["items"][0]["fund_name"] == "Текущие расходы"
    assert data["items"][0]["allocated"] == 100000


def test_distribute_overflow_first_fund(client, auth_headers):
    """Доход больше первого фонда — 10% в инвестиции, 90% дальше."""
    _setup_cascade(client, auth_headers)
    r = client.post("/funds/distribute", json={
        "amount": 250000,
    }, headers=auth_headers)
    data = r.json()
    # Первый фонд: 205000
    assert data["items"][0]["allocated"] == 205000
    # Остаток = 45000, из них 10% = 4500 в инвестиции
    inv_items = [i for i in data["investment_items"] if "10%" in i["source"]]
    assert len(inv_items) >= 1
    assert inv_items[0]["allocated"] == 4500.0
    # 90% = 40500 → следующие фонды
    assert data["items"][1]["fund_name"] == "Я"
    assert data["items"][1]["allocated"] == 30000
    assert data["items"][2]["fund_name"] == "Резервный"
    assert data["items"][2]["allocated"] == 10500  # остаток


def test_distribute_all_full(client, auth_headers):
    """Доход больше всех фондов — остаток по правилу -1 (90% в инвестиции)."""
    _setup_cascade(client, auth_headers)
    r = client.post("/funds/distribute", json={
        "amount": 400000,
    }, headers=auth_headers)
    data = r.json()
    # Все slots заполнены: 205000 + 30000 + 25000 = 260000
    # Первый split (10%): (400000 - 205000) * 0.10 = 19500
    # Остаток после slots + split: 400000 - 205000 - 19500 - 30000 - 25000 = 120500
    # Правило -1 (90%): 120500 * 0.90 = 108450
    after_all = [i for i in data["investment_items"] if "после всех" in i.get("source", "")]
    assert len(after_all) >= 1


def test_distribute_no_cascade(client, auth_headers):
    """Без каскада — пустой результат."""
    r = client.post("/funds/distribute", json={
        "amount": 100000,
    }, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["investment_items"] == []


def test_distribute_with_deposit_income_no_tax_settings(client, auth_headers):
    """Доход от вкладов без настроек НДФЛ — tax_deduction = null."""
    _setup_cascade(client, auth_headers)
    r = client.post("/funds/distribute", json={
        "amount": 50000, "is_deposit_income": True,
    }, headers=auth_headers)
    data = r.json()
    assert data["tax_deduction"] is None


def test_distribute_with_deposit_income_below_threshold(client, auth_headers):
    """Доход от вкладов ниже порога — НДФЛ = 0."""
    _setup_cascade(client, auth_headers)
    client.post("/settings/tax", json={
        "year": 2026, "tax_free_threshold": 160000,
    }, headers=auth_headers)
    r = client.post("/funds/distribute", json={
        "amount": 50000, "is_deposit_income": True,
    }, headers=auth_headers)
    data = r.json()
    assert data["tax_deduction"] is None


def test_distribute_with_deposit_income_above_threshold(client, auth_headers):
    """Доход от вкладов выше порога — НДФЛ 13%."""
    funds = _setup_cascade(client, auth_headers)
    # Создаём placement фонд и накапливаем YTD доход
    cp = client.post("/counterparties", json={"name": "Банк"}, headers=auth_headers)
    contract_id = cp.json()["contracts"][0]["id"]
    pf = client.post("/funds", json={
        "name": "Вклад Банк", "type": "placement", "contract_id": contract_id
    }, headers=auth_headers)
    pfid = pf.json()["id"]
    # YTD = 150000 (ниже порога 160000)
    client.post("/transactions", json={
        "date": "2026-01-15T00:00:00", "amount": 150000, "type": "income", "fund_id": pfid
    }, headers=auth_headers)
    client.post("/settings/tax", json={
        "year": 2026, "tax_free_threshold": 160000,
    }, headers=auth_headers)
    # Новый доход 50000 → YTD станет 200000
    # Облагаемая часть: 200000 - 160000 = 40000 × 13% = 5200
    r = client.post("/funds/distribute", json={
        "amount": 50000, "is_deposit_income": True,
    }, headers=auth_headers)
    data = r.json()
    assert data["tax_deduction"] is not None
    assert data["tax_deduction"]["amount"] == 5200.0
