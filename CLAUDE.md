# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды, счета, иерархические категории, операции. Интерфейс на русском языке.

---

## Стек технологий

### Backend
- **Python 3.x** + **FastAPI 0.115** — REST API, автодокументация `/docs`
- **SQLAlchemy 2.0** — ORM, модели в `backend/models.py`
- **SQLite** — `backend/finance.db` (без миграций, только `metadata.create_all`)
- **Uvicorn 0.30** — ASGI-сервер
- **python-jose + passlib[bcrypt]** — JWT-аутентификация
- **Pydantic 2.9** — валидация запросов/ответов

### Frontend
- **Vanilla HTML5 / CSS3 / JavaScript (ES6+)** — без фреймворков
- **Fetch API** — взаимодействие с backend
- **localStorage / sessionStorage** — хранение JWT-токена
- Утилиты инлайновые в каждой странице: `fmt()`, `fmtDate()`, `escHtml()`

### Запуск
```bash
cd backend && uvicorn main:app --reload
```
Frontend — статичные HTML-файлы, открываются через `file://` или HTTP-сервер.

---

## Структура папок

```
finance/
├── backend/
│   ├── main.py              # FastAPI, CORS, роутеры
│   ├── models.py            # SQLAlchemy ORM-модели
│   ├── database.py          # SQLite-соединение, сессии
│   ├── auth.py              # JWT, get_current_user
│   ├── requirements.txt
│   ├── finance.db
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login
│       ├── funds.py         # /funds CRUD
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       └── transactions.py  # /transactions CRUD + фильтры
├── frontend/
│   ├── index.html           # Вход / Регистрация
│   ├── dashboard.html       # Главная, карточки фондов
│   ├── accounts.html        # CRUD счетов
│   ├── funds.html           # CRUD фондов
│   ├── categories.html      # Справочники (виды/группы/статьи)
│   ├── operations.html      # Транзакции с фильтрами
│   ├── css/style.css        # Устаревшие стили (не используются)
│   └── js/app.js            # Устаревший файл (не подключается)
├── README.md
├── task.md
└── CLAUDE.md
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
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| type | Enum | `current` / `investment` |
| created_at | DateTime | |

### `accounts`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| balance | Float | default 0.0 |
| created_at | DateTime | |

### `categories`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| type | Enum | `income` / `expense` / NULL |
| level | Integer 1–4 | 4=вид, 3=группа, 2=статья, 1=резерв |
| parent_id | FK → categories | SET NULL on delete, nullable |
| sort_order | Integer | default 0 |
| created_at | DateTime | |

Иерархия: Level 4 (корень, без parent) → Level 3 (тип: income/expense) → Level 2. Нельзя удалить с дочерними. Перемещение через `PATCH /categories/{id}/move`.

### `transactions`
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE, индекс |
| date | DateTime | NOT NULL, индекс |
| amount | Float | > 0 (CheckConstraint) |
| type | Enum | `income` / `expense` |
| fund_id | FK → funds | RESTRICT DELETE |
| account_id | FK → accounts | SET NULL on delete, nullable |
| category_id | FK → categories | RESTRICT DELETE |
| comment | Text | nullable |
| created_at | DateTime | |

---

## Соглашения по коду

### Backend
- Роутеры — отдельные файлы в `backend/routers/`, подключаются через `app.include_router()`
- Pydantic-схемы определяются в файлах роутеров
- Данные изолируются фильтром `user_id == current_user.id` в каждом запросе
- HTTP-статусы: 201 создание, 204 удаление, 401 неавторизован, 404 не найдено, 409 конфликт
- Ошибки логируются через `traceback.print_exc()` в middleware
- `PUT /categories/{id}` — обновляет name/type/sort_order (level и parent_id не трогает)
- `PATCH /categories/{id}/move` — меняет level/parent_id/sort_order, рекурсивно обновляет дочерние уровни

### Frontend
- Токен: `localStorage` (remember me) или `sessionStorage`
- Заголовок `Authorization: Bearer <token>` на все защищённые запросы
- Утилиты инлайновые: `fmt(amount)` → рубли, `fmtDate(iso)` → DD.MM.YYYY HH:MM, `escHtml(s)` → XSS
- CSS-переменные: `--blue: #1a6dff`, `--green: #16a34a`, `--red: #dc2626`, `--bg: #f5f7fb`, `--text: #111827`

---

## Архитектурные решения

1. **SQLite без миграций** — при изменении моделей удалять и пересоздавать `finance.db` (или ALTER TABLE вручную).
2. **Фонды vs Счета** — Фонд — логическая единица бюджета, Счёт — физическое хранилище. Транзакция обязательно привязана к фонду, счёт опционален.
3. **Баланс фонда** — вычисляется на лету как `SUM(income) - SUM(expenses)`. Баланс счёта хранится как явное поле.
4. **Иерархия категорий** — 3 уровня (4/3/2): вид → [Доходы/Расходы] → группа → статья. В дереве уровень 3 сгруппирован по type под визуальными разделителями.
5. **JWT без refresh-токенов** — 24-часовой токен, при истечении — повторный логин.
6. **CORS** — разрешены все источники (только для локальной разработки).
