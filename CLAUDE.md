# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды, счета, иерархические категории, операции доходов и расходов. Интерфейс на русском языке.

---

## Стек технологий

### Backend
- **Python 3.x** + **FastAPI 0.115** — REST API, автодокументация `/docs`
- **SQLAlchemy 2.0** — ORM, модели в `backend/models.py`
- **SQLite** — база данных `backend/finance.db` (без миграций, только `metadata.create_all`)
- **Uvicorn 0.30** — ASGI-сервер
- **python-jose + passlib[bcrypt]** — JWT-аутентификация, хэширование паролей
- **Pydantic 2.9** — валидация запросов/ответов

### Frontend
- **Vanilla HTML5 / CSS3 / JavaScript (ES6+)** — без фреймворков и сборщиков
- **Fetch API** — взаимодействие с backend
- **localStorage / sessionStorage** — хранение JWT-токена
- Каждая страница содержит встроенные утилиты: `fmt()`, `fmtDate()`, `escHtml()` (инлайн JS)
- `frontend/js/app.js` — устаревший файл, страницами не подключается

### Запуск
```bash
cd backend && uvicorn main:app --reload
```
Frontend открывается как статичные HTML-файлы напрямую из браузера (`file://` или через простой HTTP-сервер).

---

## Структура папок

```
finance/
├── backend/
│   ├── main.py              # Точка входа FastAPI, CORS, подключение роутеров
│   ├── models.py            # SQLAlchemy ORM-модели
│   ├── database.py          # SQLite-соединение, сессии
│   ├── auth.py              # JWT-логика, get_current_user dependency
│   ├── requirements.txt
│   ├── finance.db           # SQLite-файл
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login
│       ├── funds.py         # /funds CRUD
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       └── transactions.py  # /transactions CRUD + фильтры
├── frontend/
│   ├── index.html           # Вход / Регистрация
│   ├── dashboard.html       # Главная страница
│   ├── accounts.html        # Управление счетами
│   ├── funds.html           # Управление фондами
│   ├── categories.html      # Справочники (виды деятельности / группы / статьи)
│   ├── operations.html      # Операции с фильтрами и начальными остатками
│   ├── css/style.css        # Общие стили (не используется новыми страницами)
│   └── js/app.js            # Устаревший файл (не подключается)
├── README.md
├── task.md                  # Спецификация задач разработки
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

---

### `funds` (Фонды)
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| type | Enum | `current` / `investment` |
| created_at | DateTime | |

Баланс — вычисляемое поле: сумма доходов минус расходы по связанным транзакциям.

---

### `accounts` (Счета — физические хранилища)
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| balance | Float | default 0.0 |
| created_at | DateTime | |

---

### `categories` (Иерархические категории)
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE |
| name | String(255) | |
| type | Enum | `income` / `expense` / NULL |
| level | Integer 1–4 | см. ниже |
| parent_id | FK → categories | SET NULL on delete, nullable |
| sort_order | Integer | default 0 |
| created_at | DateTime | |

**Иерархия уровней:**
- **Level 4** — Виды деятельности (корень, без родителя): Операционная, Инвестиционная, Финансовая
- **Level 3** — Группы (parent = level 4)
- **Level 2** — Статьи (parent = level 3)
- **Level 1** — зарезервирован

Бизнес-правила: нельзя удалить категорию с дочерними; level 4 не имеет parent_id; level 2 требует parent_id.

---

### `transactions` (Операции)
| Поле | Тип | Описание |
|------|-----|---------|
| id | Integer PK | |
| user_id | FK → users | CASCADE DELETE, индекс |
| date | DateTime | NOT NULL, индекс |
| amount | Float | > 0 (CheckConstraint) |
| type | Enum | `income` / `expense` |
| fund_id | FK → funds | RESTRICT DELETE, индекс |
| account_id | FK → accounts | SET NULL on delete, nullable, индекс |
| category_id | FK → categories | RESTRICT DELETE, индекс |
| comment | Text | nullable |
| created_at | DateTime | |

---

## API Endpoints

**Base URL:** `http://127.0.0.1:8000`
**Swagger UI:** `http://127.0.0.1:8000/docs`
**Auth:** `Authorization: Bearer <JWT>` (HS256, срок 24ч)

### Аутентификация
| Метод | Путь | Описание |
|-------|------|---------|
| POST | `/auth/register` | Регистрация `{name, email, password}` → `{access_token, user_id, name, email}` (201) |
| POST | `/auth/login` | Вход `{email, password}` → `{access_token, user_id, name, email}` (200) |

### Фонды `/funds` (Protected)
| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/funds` | Список фондов с рассчитанным балансом |
| POST | `/funds` | Создать `{name, type}` (201) |
| PUT | `/funds/{id}` | Обновить `{name?, type?}` |
| DELETE | `/funds/{id}` | Удалить (204) |

### Счета `/accounts` (Protected)
| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/accounts` | Список счетов |
| POST | `/accounts` | Создать `{name, balance?}` (201) |
| PUT | `/accounts/{id}` | Обновить `{name?, balance?}` |
| DELETE | `/accounts/{id}` | Удалить (204) |

### Категории `/categories` (Protected)
| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/categories` | Список, query: `type?`, `parent_id?`; сортировка: level→sort_order→name |
| POST | `/categories` | Создать `{name, type?, level?, parent_id?, sort_order?}` (201) |
| PUT | `/categories/{id}` | Обновить `{name?, type?, sort_order?}` (level и parent_id не меняются) |
| DELETE | `/categories/{id}` | Удалить (204); ошибка если есть дочерние |

### Транзакции `/transactions` (Protected)
| Метод | Путь | Описание |
|-------|------|---------|
| GET | `/transactions` | Список с фильтрами: `date_from?`, `date_to?`, `fund_id?`, `account_id?`, `category_id?`, `type?`; сортировка: date DESC, id DESC |
| POST | `/transactions` | Создать `{date, amount, type, fund_id, category_id, account_id?, comment?}` (201) |
| PUT | `/transactions/{id}` | Обновить любые поля |
| DELETE | `/transactions/{id}` | Удалить (204) |

---

## Готовые страницы фронтенда

| Файл | Статус | Описание |
|------|--------|---------|
| `index.html` | Готово | Вход / Регистрация. Табы, remember me, редирект на dashboard если залогинен |
| `dashboard.html` | Готово | Карточки фондов с балансами, последние 10 транзакций, skeleton-loading |
| `accounts.html` | Готово | CRUD счетов, ввод начальных остатков |
| `funds.html` | Готово | CRUD фондов |
| `categories.html` | Готово | 3 таба: Виды деятельности (lvl 4) / Группы (lvl 3) / Статьи (lvl 2) |
| `operations.html` | Готово | Полный список транзакций с фильтрами, ввод начальных остатков |
| `settings.html` | Не создан | Настройки пользователя |
| `profile.html` | Не создан | Профиль пользователя |

Все страницы имеют общую боковую навигацию (sidebar) с пунктами: Главная, Фонды, Счета, Операции, Справочники, Настройки, Профиль.

---

## Соглашения по коду

### Backend
- Все роутеры — отдельные файлы в `backend/routers/`, подключаются в `main.py` через `app.include_router()`
- Pydantic-схемы определяются в файлах роутеров (не вынесены отдельно)
- Данные пользователя изолируются фильтром `user_id == current_user.id` в каждом запросе
- HTTP-статусы: 201 на создание, 204 на удаление, 401 на неавторизованный доступ, 404 на не найдено, 409 на конфликт
- Логирование ошибок через `traceback.print_exc()` в middleware

### Frontend
- Токен хранится в `localStorage` (remember me) или `sessionStorage`
- Заголовок `Authorization: Bearer <token>` добавляется ко всем защищённым запросам
- Утилиты инлайновые в каждой странице: `fmt(amount)` → рубли, `fmtDate(iso)` → DD.MM.YYYY HH:MM, `escHtml(s)` → XSS-защита
- Цветовая схема (CSS-переменные): `--blue: #1a6dff`, `--green: #16a34a` (доходы), `--red: #dc2626` (расходы), `--bg: #f5f7fb`, `--text: #111827`

---

## Важные архитектурные решения

1. **SQLite без миграций** — схема создаётся через `Base.metadata.create_all()` при старте. При изменении моделей нужно удалять и пересоздавать `finance.db` (или делать ALTER TABLE вручную).

2. **Фонды vs Счета** — концептуальное разделение: Фонд — логическая единица (операционный/инвестиционный бюджет), Счёт — физическое место хранения (карта, наличные). Транзакция обязательно привязана к фонду, но необязательно к счёту.

3. **Баланс фонда** — не хранится в БД, вычисляется на лету как `SUM(income) - SUM(expenses)` по транзакциям. Баланс счёта хранится как явное поле.

4. **Иерархия категорий** — 3 уровня (4/3/2), level 1 зарезервирован. Используется для построения отчётов по видам деятельности (операционная/инвестиционная/финансовая деятельность — стандарт МСФО/GAAP).

5. **JWT без refresh-токенов** — простая схема с 24-часовым токеном. При истечении — повторный логин.

6. **CORS** — разрешены все источники (для локальной разработки). В продакшне нужно ограничить.

7. **Нет системы тестов** — тестирование только через Swagger UI (`/docs`) и браузер.

8. **Язык интерфейса** — русский. Форматирование дат и валюты через `toLocaleString('ru-RU')`.
