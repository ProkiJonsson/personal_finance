# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды (6 типов), счета, иерархические категории, операции, контрагенты, договоры, каскадное распределение дохода с историей, НДФЛ на вклады. Интерфейс на русском языке.

---

## Стек технологий

**Backend:** Python 3.x + FastAPI 0.115, SQLAlchemy 2.0, SQLite (`backend/finance.db`), Uvicorn 0.30, python-jose + passlib[bcrypt], Pydantic 2.9. Документация: `/docs`.

**Frontend:** Vanilla HTML5 / CSS3 / JavaScript ES6+, Fetch API, localStorage/sessionStorage. Утилиты инлайновые: `fmt()`, `fmtDateRu()`, `escHtml()`.

**Запуск:** `cd backend && uvicorn main:app --reload`. Frontend — статичные HTML-файлы через `file://` или HTTP-сервер.

---

## Структура папок

```
finance/
├── backend/
│   ├── main.py              # FastAPI, CORS (перед роутерами), роутеры
│   ├── models.py            # SQLAlchemy ORM-модели (14 моделей)
│   ├── database.py          # SQLite-соединение, сессии
│   ├── auth.py              # JWT, get_current_user
│   ├── init_db.sql          # Дамп схемы для развёртывания
│   ├── uploads/             # Вложения файлов (PDF, JPEG, PNG)
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login
│       ├── funds.py         # /funds CRUD + distribute + distributions
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       ├── transactions.py  # /transactions CRUD + фильтры
│       ├── counterparties.py # /counterparties CRUD + /contracts
│       ├── cascades.py      # /cascades CRUD (расклад)
│       ├── settings.py      # /settings (AppSetting + НДФЛ)
│       └── attachments.py   # /attachments upload/download
├── frontend/
│   ├── index.html           # Вход / Регистрация
│   ├── dashboard.html       # Главная, карточки фондов
│   ├── accounts.html        # CRUD счетов
│   ├── funds.html           # CRUD фондов + распределение дохода
│   ├── categories.html      # Статьи учёта (виды/группы/статьи)
│   ├── operations.html      # Транзакции с фильтрами
│   ├── counterparties.html  # Контрагенты + договоры + вложения
│   ├── cascade.html         # Расклад (каскады)
│   ├── settings.html        # Настройки (фонды, НДФЛ, лимиты)
│   ├── css/
│   │   ├── sidebar.css      # Стили боковой панели
│   │   └── common.css       # Общие CSS-переменные и базовые стили
│   └── js/
│       └── layout.js        # Инъекция sidebar и header на все страницы
└── .mcp.json                # MCP-серверы (Playwright)
```

---

## Таблицы БД (14 моделей)

`users` — пользователи (email, password_hash, bcrypt). CASCADE DELETE на все дочерние.

`counterparties` — контрагенты (name, description). При создании авто-создаётся договор "Основной".

`contracts` — договоры контрагентов (name, description). "Основной" нельзя удалить.

`funds` — фонды 6 типов: budget/investment/tax_reserve/debt/loan/placement. Поля: name, description, type, contract_id (nullable), is_archived, is_system.

`accounts` — счета (name, balance).

`categories` — иерархия 4 уровней: Level 4 (вид деятельности) → 3 (тип: income/expense) → 2 (группа) → 1 (статья).

`transactions` — операции (date, amount>0, type, fund_id nullable, account_id, category_id, comment, is_initial).

`cascades` + `cascade_slots` + `split_rules` — каскад распределения дохода. Slots: fund_id + target_amount + sort_order. Rules: trigger_position (NULL=от рубля, 0..N=после позиции, -1=после всех) + target_fund_id + percentage (0..1). Трек обнуляется каждый месяц.

`distribution_logs` + `distribution_log_items` — история распределений дохода (amount, month YYYY-MM, is_deposit_income). Items: fund_id, fund_name, allocated, source.

`tax_settings` — НДФЛ на вклады по годам (прогрессивный: 0%/13%/15%).

`app_settings` — fund_accounting_enabled, max_attachment_size_mb.

`attachments` — полиморфные вложения (entity_type: contract/transaction). PDF/JPEG/PNG до 10 МБ.

---

## Соглашения по коду

### Backend
- Роутеры в `backend/routers/`, подключаются через `app.include_router()`
- CORS middleware подключается **перед** роутерами в `main.py`
- Pydantic-схемы определяются в файлах роутеров
- Данные изолируются `user_id == current_user.id`
- HTTP-статусы: 201 создание, 204 удаление, 401 неавторизован, 404 не найдено, 409 конфликт
- В `funds.py` маршруты `/distribute`, `/distribute/confirm`, `/distributions` регистрируются **до** `/{fund_id}`
- В `cascades.py` маршрут `/active` регистрируется **до** `/{cascade_id}`
- В `categories.py` маршрут `/clear-user-data` **до** `/{category_id}`

### Frontend
- Токен: `localStorage` (remember me) или `sessionStorage`
- `Authorization: Bearer <token>` на все защищённые запросы
- CSS-переменные в `css/common.css`
- `js/layout.js` — инъекция sidebar/header, скрытие `[data-fund-feature]` если fund_accounting выключен
- Sidebar: основная секция (Главная, Операции, Фонды, Счета) + bottom (Каскад Фондов, Контрагенты, Статьи учёта, Настройки, Выход)
- Тип фонда — кнопки `.btn-select-group`
- Модалки **не закрываются** по клику за пределами окна
- Каскад: "Принцип" (не "Триггер"), валидация суммы % ≤ 100 на один принцип

**Тесты:** `cd backend && python -m pytest tests/ -v` (53 теста, in-memory SQLite + StaticPool)

---

## API endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| POST | /auth/register, /auth/login | Авторизация |
| GET/POST/PUT/DELETE | /funds | CRUD фондов |
| POST | /funds/distribute | Preview распределения дохода |
| POST | /funds/distribute/confirm | Подтвердить + сохранить в историю |
| GET | /funds/distributions | История распределений |
| GET/POST/PUT/DELETE | /accounts | CRUD счетов |
| GET/POST/PUT/DELETE | /categories | CRUD категорий |
| GET/POST/PUT/DELETE | /transactions | CRUD операций |
| GET/POST/PUT/DELETE | /counterparties | CRUD контрагентов |
| GET/POST/PUT/DELETE | /counterparties/{id}/contracts | Договоры |
| GET/POST/PUT/DELETE | /cascades | Каскады |
| GET | /cascades/active | Активный каскад |
| POST | /cascades/{id}/copy | Копировать каскад |
| GET/PUT | /settings | Настройки |
| GET/POST/DELETE | /settings/tax | НДФЛ по годам |
| POST/GET/DELETE | /attachments | Вложения файлов |

---

## Архитектурные решения

1. **SQLite без миграций** — при изменении моделей: `Base.metadata.create_all()` для новых таблиц, удаление DB для изменения существующих.
2. **Фонды vs Счета** — Фонд — логическая единица (6 типов), Счёт — физическое хранилище. fund_id nullable.
3. **Баланс фонда** — `SUM(income) - SUM(expenses)` на лету.
4. **Каскад** — дата-версионная конфигурация. Трек обнуляется ежемесячно (`_get_month_income`). `POST /funds/distribute` — preview, confirm — сохраняет лог + создаёт транзакции.
5. **Контрагенты → Договоры → Фонды** — Fund.contract_id через договор.
6. **НДФЛ** — прогрессивный расчёт. Системный фонд is_system=True.
7. **JWT** — 24-часовой токен, без refresh.
8. **CORS** — `allow_origins=["*"]`, middleware перед роутерами.
