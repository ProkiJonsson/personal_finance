# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды (6 типов), счета, иерархические категории, операции, контрагенты, договоры, каскадное распределение дохода, НДФЛ на вклады. Интерфейс на русском языке.

---

## Стек технологий

**Backend:** Python 3.x + FastAPI 0.115, SQLAlchemy 2.0, SQLite (`backend/finance.db`), Uvicorn 0.30, python-jose + passlib[bcrypt], Pydantic 2.9. Документация: `/docs`.

**Frontend:** Vanilla HTML5 / CSS3 / JavaScript ES6+, Fetch API, localStorage/sessionStorage. Утилиты инлайновые: `fmt()`, `fmtDate()`, `escHtml()`.

**Запуск:** `cd backend && uvicorn main:app --reload`. Frontend — статичные HTML-файлы через `file://` или HTTP-сервер.

---

## Структура папок

```
finance/
├── backend/
│   ├── main.py              # FastAPI, CORS, роутеры
│   ├── models.py            # SQLAlchemy ORM-модели
│   ├── database.py          # SQLite-соединение, сессии
│   ├── auth.py              # JWT, get_current_user
│   ├── init_db.sql          # Дамп схемы для развёртывания на сервере
│   ├── uploads/             # Вложения файлов (PDF, JPEG, PNG)
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login
│       ├── funds.py         # /funds CRUD + POST /funds/distribute
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       ├── transactions.py  # /transactions CRUD + фильтры
│       ├── counterparties.py # /counterparties CRUD + /contracts
│       ├── cascades.py      # /cascades CRUD (расклад)
│       ├── settings.py      # /settings (AppSetting + НДФЛ)
│       └── attachments.py   # /attachments upload/download
└── frontend/
    ├── index.html           # Вход / Регистрация
    ├── dashboard.html       # Главная, карточки фондов
    ├── accounts.html        # CRUD счетов
    ├── funds.html           # CRUD фондов (6 типов, группировка)
    ├── categories.html      # Статьи учёта (виды/группы/статьи)
    ├── operations.html      # Транзакции с фильтрами
    ├── counterparties.html  # Контрагенты + договоры + вложения
    ├── cascade.html         # Расклад (каскады)
    ├── settings.html        # Настройки (фонды, НДФЛ, лимиты)
    ├── css/
    │   ├── sidebar.css      # Стили боковой панели
    │   └── common.css       # Общие CSS-переменные и базовые стили
    └── js/
        └── layout.js        # Инъекция sidebar и header на все страницы
```

---

## Таблицы БД

### `users`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| name | String(255) | |
| email | String(255) UNIQUE | Индекс |
| password_hash | String(255) | bcrypt |
| created_at | DateTime | server_default |

Связи: `funds`, `accounts`, `categories`, `transactions`, `counterparties`, `cascades`, `tax_settings`, `app_setting`, `attachments` — CASCADE DELETE.

### `counterparties`
| Поле | Тип | |
|------|-----|-|
| id | Integer PK | |
| user_id | FK → users CASCADE | |
| name | String(255) | |
| description | Text | nullable |

### `contracts`
| Поле | Тип | |
|------|-----|-|
| id | Integer PK | |
| counterparty_id | FK → counterparties CASCADE | |
| name | String(255) | default "Основной" |
| description | Text | nullable |

При создании контрагента автоматически создаётся договор "Основной". Нельзя удалить "Основной" и договор с привязанными фондами.

### `funds`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users CASCADE | |
| name | String(255) | |
| description | Text | nullable |
| type | Enum(FundType) | `budget`/`investment`/`tax_reserve`/`debt`/`loan`/`placement` |
| contract_id | FK → contracts | nullable, SET NULL |
| is_archived | Boolean | default False |
| is_system | Boolean | default False (для "Налоги на вклады") |

**Конвенция знаков:** loan=+ (актив), debt=− (обязательство), placement=+ (размещено).

### `accounts`
| Поле | Тип | |
|------|-----|-|
| id | Integer PK | |
| user_id | FK → users CASCADE | |
| name | String(255) | |
| balance | Float | default 0.0 |

### `categories`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users CASCADE | |
| name | String(255) | |
| type | Enum | `income` / `expense` / NULL |
| level | Integer 1–4 | 4=вид деятельности, 3=тип операции, 2=группа, 1=статья |
| parent_id | FK → categories | nullable, SET NULL on delete |
| sort_order | Integer | default 0 |

**Иерархия:** Level 4 (Вид деятельности, корень) → Level 3 (Тип операции: income/expense) → Level 2 (Группа) → Level 1 (Статья).

### `transactions`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users CASCADE | индекс |
| date | DateTime | NOT NULL, индекс |
| amount | Float | > 0 (CheckConstraint) |
| type | Enum | `income` / `expense` |
| fund_id | FK → funds | **nullable** (если учёт по фондам выключен), RESTRICT DELETE |
| account_id | FK → accounts | SET NULL, nullable |
| category_id | FK → categories | RESTRICT DELETE, nullable |
| comment | Text | nullable |

### `cascades` + `cascade_slots` + `split_rules`
Каскад — конфигурация распределения дохода, действует с `effective_from`.
- `cascade_slots`: fund_id + target_amount + sort_order
- `split_rules`: trigger_position (NULL=от рубля, 0..N=после позиции, -1=после всех) + target_fund_id + percentage (0..1)

### `tax_settings`
НДФЛ на вклады по годам: tax_free_threshold, rate_standard (0.13), rate_elevated (0.15), elevated_threshold (2M). Прогрессивный расчёт от накопленного за год.

### `app_settings`
fund_accounting_enabled (Boolean), max_attachment_size_mb (Integer, default 10).

### `attachments`
Полиморфные вложения (entity_type: `contract`/`transaction` + entity_id). PDF/JPEG/PNG до 10 МБ. Файлы в `backend/uploads/{user_id}/{entity_type}/`.

---

## Соглашения по коду

### Backend
- Роутеры — отдельные файлы в `backend/routers/`, подключаются через `app.include_router()`
- Pydantic-схемы определяются в файлах роутеров
- Данные изолируются фильтром `user_id == current_user.id` в каждом запросе
- HTTP-статусы: 201 создание, 204 удаление, 401 неавторизован, 404 не найдено, 409 конфликт
- В `categories.py` маршрут `/clear-user-data` должен быть зарегистрирован **до** `/{category_id}`
- В `funds.py` маршруты `/distribute` регистрируются **до** `/{fund_id}`
- В `cascades.py` маршрут `/active` регистрируется **до** `/{cascade_id}`

### Frontend
- Токен: `localStorage` (remember me) или `sessionStorage`
- Заголовок `Authorization: Bearer <token>` на все защищённые запросы
- CSS-переменные определены в `css/common.css`
- `js/layout.js` подключается последним скриптом на каждой странице — инъектирует sidebar и header
- Элементы с `data-fund-feature` скрываются если `fund_accounting_enabled=false` (проверяется через `GET /settings` в layout.js)
- Sidebar: основная секция (Главная, Операции, Фонды, Счета) + bottom (Каскад Фондов, Контрагенты, Статьи учёта, Настройки, Выход)
- Тип фонда в модалке выбирается кнопками `.btn-select-group` (как в categories.html)

**Тесты:** `cd backend && python -m pytest tests/ -v` (53 теста, in-memory SQLite + StaticPool)

---

## Архитектурные решения

1. **SQLite без миграций** — при изменении моделей удалять и пересоздавать `finance.db`.
2. **Фонды vs Счета** — Фонд — логическая единица бюджета (6 типов), Счёт — физическое хранилище. fund_id теперь nullable (опция учёта по фондам).
3. **Баланс фонда** — вычисляется на лету как `SUM(income) - SUM(expenses)`.
4. **Каскад (расклад)** — дата-версионная конфигурация: slots (фонды+цели+порядок) + split_rules (правила отщепления %). Полуавтомат: `POST /funds/distribute` возвращает preview.
5. **Контрагенты → Договоры → Фонды** — Fund привязан к contract_id (через договор к контрагенту).
6. **НДФЛ на вклады** — прогрессивный расчёт от накопленного за год. Системный фонд "Налоги на вклады" (is_system=True) создаётся автоматически.
7. **JWT без refresh-токенов** — 24-часовой токен.
8. **CORS** — разрешены все источники (только для локальной разработки).
