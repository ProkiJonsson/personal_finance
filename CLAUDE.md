# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами: фонды (6 типов), счета, иерархические категории, операции, контрагенты, договоры, каскадное распределение дохода с историей, НДФЛ на вклады. Админ-панель с WYSIWYG-редактором контента страниц. Интерфейс на русском языке.

---

## Стек технологий

**Backend:** Python 3.x + FastAPI 0.115, SQLAlchemy 2.0, SQLite (`backend/finance.db`), Uvicorn 0.30, python-jose + passlib[bcrypt], Pydantic 2.9. Документация: `/docs`.

**Frontend:** Vanilla HTML5 / CSS3 / JavaScript ES6+, Fetch API, localStorage/sessionStorage. Утилиты инлайновые: `fmt()`, `fmtDateRu()`, `escHtml()`. Глобальные утилиты в `js/layout.js`: `formatMoney()`, `parseMoney()`, `initMoneyInput()`.

**Запуск:** `cd backend && uvicorn main:app --reload`. Frontend — статичные HTML-файлы через `file://` или HTTP-сервер.

---

## Структура папок

```
finance/
├── backend/
│   ├── main.py              # FastAPI, CORS (перед роутерами), роутеры
│   ├── models.py            # SQLAlchemy ORM-модели (18 моделей)
│   ├── database.py          # SQLite-соединение, сессии
│   ├── auth.py              # JWT, get_current_user, get_current_user_any, get_admin_user
│   ├── init_db.sql          # Дамп схемы для развёртывания
│   ├── uploads/             # Вложения файлов (PDF, JPEG, PNG)
│   └── routers/
│       ├── auth.py          # /auth/register, /auth/login, /auth/me
│       ├── funds.py         # /funds CRUD + distribute + distributions
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (иерархия)
│       ├── transactions.py  # /transactions CRUD + фильтры
│       ├── counterparties.py # /counterparties CRUD + /contracts
│       ├── cascades.py      # /cascades CRUD (расклад)
│       ├── settings.py      # /settings (AppSetting + НДФЛ)
│       ├── attachments.py   # /attachments upload/download
│       └── admin.py         # /admin (page-content, settings, users, upload-image)
├── frontend/
│   ├── index.html           # Вход / Регистрация
│   ├── dashboard.html       # Главная, карточки фондов
│   ├── accounts.html        # CRUD счетов
│   ├── funds.html           # CRUD фондов + распределение дохода
│   ├── categories.html      # Статьи учёта (виды/группы/статьи, без вкладок)
│   ├── operations.html      # Транзакции с фильтрами
│   ├── counterparties.html  # Контрагенты + договоры + вложения
│   ├── cascade.html         # Расклад (каскады)
│   ├── settings.html        # Настройки (фонды, виды деятельности, НДФЛ)
│   ├── admin.html           # Админ-панель (пользователи, глобальные настройки, контент страниц, Quill)
│   ├── css/
│   │   ├── sidebar.css      # Стили боковой панели
│   │   └── common.css       # Общие CSS-переменные и базовые стили
│   └── js/
│       └── layout.js        # Инъекция sidebar и header на все страницы
└── .mcp.json                # MCP-серверы (Playwright)
```

---

## Таблицы БД (18 моделей)

`users` — пользователи (id: UUID v4 String(36), email, password_hash, is_admin, is_active, bcrypt). CASCADE DELETE на все дочерние. Все дочерние таблицы: `user_id` String(36). Новые пользователи `is_active=False` — требуют активации админом. Первый админ назначается вручную в БД (`is_admin=1, is_active=1`).

`counterparties` — контрагенты (name, description). При создании авто-создаётся договор "Основной".

`contracts` — договоры контрагентов (name, description). "Основной" нельзя удалить.

`funds` — фонды 6 типов: budget/investment/tax_reserve/debt/loan/placement. Поля: name, description, type, contract_id (nullable), is_archived, is_system.

`accounts` — счета (name, balance).

`categories` — иерархия 4 уровней: Level 4 (вид деятельности) → 3 (тип: income/expense) → 2 (группа) → 1 (статья).

`transactions` — операции (date, amount>0, type, fund_id nullable, account_id, category_id, comment, is_initial).

`cascades` + `cascade_slots` + `split_rules` — каскад распределения дохода. Slots: fund_id + target_amount + sort_order. Rules: trigger_position (NULL=от рубля, 0..N=после позиции, -1=после всех) + target_fund_id + percentage (0..1). Трек обнуляется каждый месяц.

`distribution_logs` + `distribution_log_items` — история распределений дохода (amount, month YYYY-MM, is_deposit_income). Items: fund_id, fund_name, allocated, source.

`tax_settings` + `tax_brackets` — НДФЛ на вклады по годам. tax_settings: year, tax_free_threshold. tax_brackets: threshold_amount (порог «до»), rate (0..1), sort_order. До 5 порогов на год. Расчёт прогрессивный: каждый порог = верхняя граница зоны, доход свыше последнего порога — по последней ставке.

`app_settings` — fund_accounting_enabled (per-user).

`admin_settings` — глобальные настройки (key-value). Ключ: `max_attachment_size_mb`.

`page_content` — редактируемый контент страниц (page_key + element_key + content). UniqueConstraint(page_key, element_key). Seed-данные заполняются при старте если таблица пуста.

`attachments` — полиморфные вложения (entity_type: contract/transaction). PDF/JPEG/PNG, лимит из admin_settings.

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
- `js/layout.js` — инъекция sidebar/header, скрытие `[data-fund-feature]` если fund_accounting выключен, утилиты форматирования денежных полей (`formatMoney`, `parseMoney`, `initMoneyInput`), автообновление токена через `/auth/me`, блокировка неактивных пользователей (страница «Ожидание активации» с логотипом и автоопределением момента активации)
- Денежные поля: `type="text" inputmode="decimal" data-money`, формат "1 600 000,00". Для динамических полей вызывать `initMoneyInput(el)` после вставки в DOM
- Sidebar: основная секция (Главная, Операции, Фонды, Счета) + bottom (Каскад Фондов, Контрагенты, Статьи учёта, Админ-панель (только is_admin), Настройки, Выход)
- Тип фонда — кнопки `.btn-select-group`
- Модалки **не закрываются** по клику за пределами окна
- Каскад: "Принцип" (не "Триггер"), валидация суммы % ≤ 100 на один принцип

**Тесты:** `cd backend && python -m pytest tests/ -v` (77 тестов, in-memory SQLite + StaticPool)

---

## API endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| POST | /auth/register, /auth/login | Авторизация |
| GET | /auth/me | Обновить токен (актуальные is_admin/is_active) |
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
| GET | /admin/users?search= | Список пользователей с поиском (только админ) |
| PUT | /admin/users/{id} | Обновить is_admin/is_active пользователя (только админ) |
| GET | /admin/page-content | Контент страниц (публичный) |
| PUT | /admin/page-content | Обновить контент (только админ) |
| GET/PUT | /admin/settings | Глобальные настройки (PUT — только админ) |
| POST | /admin/upload-image | Загрузка картинки для редактора (только админ) |
| GET | /admin/images/{filename} | Отдача картинки |

---

## Архитектурные решения

1. **SQLite без миграций** — при изменении моделей: `Base.metadata.create_all()` для новых таблиц, удаление DB для изменения существующих.
2. **Фонды vs Счета** — Фонд — логическая единица (6 типов), Счёт — физическое хранилище. fund_id nullable.
3. **Баланс фонда** — `SUM(income) - SUM(expenses)` на лету.
4. **Каскад** — дата-версионная конфигурация. Трек обнуляется ежемесячно (`_get_month_income`). `POST /funds/distribute` — preview, confirm — сохраняет лог + создаёт транзакции.
5. **Контрагенты → Договоры → Фонды** — Fund.contract_id через договор.
6. **НДФЛ** — прогрессивный расчёт по порогам «до» (до 5 штук). Каждый порог = верхняя граница зоны, свыше последнего — последняя ставка. Ставки хранятся как дробь (0.13), на фронте вводятся как целые (13%). Системный фонд is_system=True.
7. **Модалки** — `max-height: calc(100vh - 48px)`, flex-раскладка (header/body/footer), `modal-body` со скроллом, кнопки всегда видны. Не закрываются по клику вне окна. Подтверждение удаления — кастомная модалка (не `confirm()`).
8. **JWT** — 24-часовой токен. Payload: `sub` (UUID строка), `name`, `is_admin`, `is_active`, `exp`. Токен автообновляется при каждой загрузке страницы через `GET /auth/me` (использует `get_current_user_any` — без проверки is_active). Это позволяет отразить изменение прав без перелогина.
9. **Виды деятельности** — toggle на `settings.html`, при переключении вызывает `/categories/clear-user-data` и редиректит на `categories.html`. На categories.html — подсказка со ссылкой на Настройки (скрывается когда режим включён).
10. **Админ-панель** — отдельная роль `is_admin` в модели User (первый админ назначается вручную в БД). Отдельная страница `admin.html`, пункт в sidebar виден только админу. Три секции: **Пользователи** (таблица с поиском, toggle «Активен» и «Админ» с модалкой подтверждения), **Глобальные настройки** (max_attachment_size_mb), **Контент страниц** (WYSIWYG Quill). Quill CDN 1.3.7, тема snow, тулбар: форматирование, цвет текста/фона, ссылки, картинки, размер шрифта, заголовки. Загрузка картинок: `POST /admin/upload-image` → `backend/uploads/admin/`. Контент подгружается на все страницы через `loadPageContent()` в `layout.js`, кэшируется в `sessionStorage`. Элементы с `data-content-key` обновляются динамически.
11. **Активация пользователей** — новые пользователи создаются с `is_active=False`. До активации админом видят страницу «Ожидание активации» (логотип + сообщение). Страница автоматически проверяет статус каждые 5 сек через `GET /settings` — при активации показывает «Аккаунт активирован!» с кнопкой «Войти в приложение». `get_current_user` возвращает 403 для неактивных. Нельзя деактивировать самого себя.
12. **Quill-контент на живых страницах** — CSS в `common.css`: `[data-content-key]` задаёт базовый `font-size: 14px`, `line-height: 1.6`. Ссылки — `color: var(--primary)`. Короткие подсказки (`.form-hint`, `#info-activity-hint`) — `<p>` рендерятся `display: inline`. Help-tip блоки — `<p>` с `margin: 0 0 4px 0`. Quill при выборе чёрного цвета удаляет атрибут — перехватывается кастомным обработчиком.
13. **CORS** — `allow_origins=["*"]`, middleware перед роутерами.
