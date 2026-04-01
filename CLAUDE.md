# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды, счета, иерархические категории, операции. Интерфейс на русском языке.

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
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login
│       ├── funds.py         # /funds CRUD
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       └── transactions.py  # /transactions CRUD + фильтры
└── frontend/
    ├── index.html           # Вход / Регистрация
    ├── dashboard.html       # Главная, карточки фондов
    ├── accounts.html        # CRUD счетов
    ├── funds.html           # CRUD фондов
    ├── categories.html      # Справочники (виды/группы/статьи)
    ├── operations.html      # Транзакции с фильтрами
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

Связи: `funds`, `accounts`, `categories`, `transactions` — CASCADE DELETE.

### `funds`
| Поле | Тип | |
|------|-----|-|
| id | Integer PK | |
| user_id | FK → users CASCADE | |
| name | String(255) | |
| type | Enum | `current` / `investment` |

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

Нельзя удалить категорию с дочерними (409). Перемещение: `PATCH /categories/{id}/move`.

**Режим учёта по видам деятельности** — опция `activityMode` хранится в `localStorage` браузера. При смене режима все категории уровней 1 и 2 удаляются через `DELETE /categories/clear-user-data` (уровни 3 и 4 сохраняются). Пользователь подтверждает действие в модальном окне.

**Автосидирование структуры** — `categories.html` при каждой загрузке (функция `ensureActivityStructure`) проверяет наличие полной иерархии level-4/level-3 и создаёт недостающие узлы через API:
- Нет level-4 совсем → создаёт 3 вида деятельности + узлы Доходы/Расходы под каждым
- Level-4 есть, но под ними нет level-3 → досоздаёт только недостающие Доходы/Расходы
- В `activityMode=OFF` автосидирование не запускается

### `transactions`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users CASCADE | индекс |
| date | DateTime | NOT NULL, индекс |
| amount | Float | > 0 (CheckConstraint) |
| type | Enum | `income` / `expense` |
| fund_id | FK → funds | RESTRICT DELETE |
| account_id | FK → accounts | SET NULL, nullable |
| category_id | FK → categories | RESTRICT DELETE |
| comment | Text | nullable |

---

## Соглашения по коду

### Backend
- Роутеры — отдельные файлы в `backend/routers/`, подключаются через `app.include_router()`
- Pydantic-схемы определяются в файлах роутеров
- Данные изолируются фильтром `user_id == current_user.id` в каждом запросе
- HTTP-статусы: 201 создание, 204 удаление, 401 неавторизован, 404 не найдено, 409 конфликт
- Ошибки логируются через `traceback.print_exc()` в middleware
- В `categories.py` маршрут `/clear-user-data` должен быть зарегистрирован **до** `/{category_id}`

### Frontend
- Токен: `localStorage` (remember me) или `sessionStorage`
- Заголовок `Authorization: Bearer <token>` на все защищённые запросы
- CSS-переменные определены в `css/common.css`: `--primary`, `--primary-dark`, `--primary-light`, `--success`, `--danger`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border`, `--bg-body`, `--bg-card-light`
- `js/layout.js` подключается последним скриптом на каждой странице — инъектирует sidebar и header

---

## Архитектурные решения

1. **SQLite без миграций** — при изменении моделей удалять и пересоздавать `finance.db` (или ALTER TABLE вручную).
2. **Фонды vs Счета** — Фонд — логическая единица бюджета, Счёт — физическое хранилище. Транзакция обязательно привязана к фонду, счёт опционален.
3. **Баланс фонда** — вычисляется на лету как `SUM(income) - SUM(expenses)`. Баланс счёта хранится как явное поле.
4. **JWT без refresh-токенов** — 24-часовой токен, при истечении — повторный логин.
5. **CORS** — разрешены все источники (только для локальной разработки).
6. **Инициализация БД на сервере** — `backend/init_db.sql` содержит схему без данных. Применяется один раз: `sqlite3 finance.db < init_db.sql`. После этого `Base.metadata.create_all` при старте бэкенда не перезаписывает существующие таблицы. Пользователи регистрируются сами; категории для режима деятельности создаются автоматически JS-кодом при первом открытии страницы справочников.
