# Finance — Личный финансовый учёт

Веб-приложение для управления личными финансами с системой фондов, каскадным распределением дохода, контрагентами и автоматическим расчётом НДФЛ.

## Возможности

- **6 типов фондов**: бюджетные, инвестиционные, налоговые резервы, долги, займы, размещения
- **Каскадное распределение дохода**: настраиваемые правила наполнения фондов с отщеплением %
- **Контрагенты и договоры**: банки, заёмщики, кредиторы с вложениями файлов
- **НДФЛ на вклады**: прогрессивный расчёт от накопленного за год (0% / 13% / 15%)
- **Счета**: банковские карты, наличные, электронные кошельки
- **Иерархические категории**: 4 уровня (вид деятельности → тип → группа → статья)
- **Операции**: доходы и расходы с фильтрами, поиском, экспортом
- **Вложения файлов**: PDF, JPEG, PNG к договорам и операциям

## Стек технологий

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.x, FastAPI 0.115, SQLAlchemy 2.0, SQLite, Pydantic 2.9 |
| Frontend | Vanilla HTML5/CSS3/JS ES6+, Fetch API |
| Авторизация | JWT (python-jose), bcrypt (passlib) |
| Тесты | pytest + httpx, 53 теста |

## Быстрый старт

```bash
# 1. Установить зависимости
cd backend
pip install -r requirements.txt

# 2. Запустить сервер
uvicorn main:app --reload

# 3. Открыть фронтенд
# Вариант A: напрямую в браузере
open frontend/index.html

# Вариант B: через HTTP-сервер (рекомендуется)
cd frontend && python -m http.server 5500
# Открыть http://localhost:5500
```

API-документация: http://127.0.0.1:8000/docs

## Структура проекта

```
finance/
├── backend/
│   ├── main.py                 # FastAPI приложение
│   ├── models.py               # 12 ORM-моделей
│   ├── database.py             # SQLite соединение
│   ├── auth.py                 # JWT авторизация
│   ├── init_db.sql             # DDL для развёртывания
│   ├── uploads/                # Вложения файлов
│   ├── routers/
│   │   ├── auth.py             # Регистрация, вход
│   │   ├── funds.py            # Фонды + распределение дохода
│   │   ├── accounts.py         # Счета
│   │   ├── categories.py       # Категории (иерархия)
│   │   ├── transactions.py     # Операции
│   │   ├── counterparties.py   # Контрагенты + договоры
│   │   ├── cascades.py         # Каскад фондов
│   │   ├── settings.py         # Настройки + НДФЛ
│   │   └── attachments.py      # Вложения файлов
│   └── tests/
│       ├── conftest.py         # Фикстуры (in-memory SQLite)
│       ├── test_auth.py        # 5 тестов
│       ├── test_funds.py       # 10 тестов
│       ├── test_transactions.py # 6 тестов
│       ├── test_counterparties.py # 10 тестов
│       ├── test_cascades.py    # 8 тестов
│       ├── test_settings.py    # 7 тестов
│       └── test_distribute.py  # 7 тестов
└── frontend/
    ├── index.html              # Вход / Регистрация
    ├── dashboard.html           # Главная
    ├── funds.html               # Фонды (6 типов, card/table view)
    ├── accounts.html            # Счета
    ├── operations.html          # Операции с фильтрами
    ├── categories.html          # Статьи учёта
    ├── counterparties.html      # Контрагенты + договоры
    ├── cascade.html             # Каскад Фондов
    ├── settings.html            # Настройки
    ├── css/                     # Стили
    └── js/layout.js             # Sidebar + header
```

## Система фондов

Фонд — виртуальный кошелёк. Каждый рубль дохода попадает в конкретный фонд.

| Тип | Назначение | Знак баланса |
|-----|-----------|-------------|
| budget | Текущие расходы (каскадное наполнение) | + |
| investment | Накопления | + |
| tax_reserve | Резерв на налоги | + |
| debt | Я должен кому-то | − |
| loan | Мне должны | + |
| placement | Вклады, брокер (физическое размещение) | + |

### Каскад

Доход распределяется как "стаканы" — каждый следующий наполняется после предыдущего. Правила отщепления позволяют направлять % в инвестиции после заполнения определённого фонда.

## Тесты

```bash
cd backend
python -m pytest tests/ -v
```

53 теста покрывают: авторизацию, CRUD фондов/контрагентов/каскадов/настроек, распределение дохода с НДФЛ, nullable fund_id.

## API endpoints

| Метод | Путь | Описание |
|-------|------|---------|
| POST | /auth/register | Регистрация |
| POST | /auth/login | Вход |
| GET/POST/PUT/DELETE | /funds | CRUD фондов |
| POST | /funds/distribute | Preview распределения дохода |
| GET/POST/PUT/DELETE | /accounts | CRUD счетов |
| GET/POST/PUT/DELETE | /categories | CRUD категорий |
| GET/POST/PUT/DELETE | /transactions | CRUD операций |
| GET/POST/PUT/DELETE | /counterparties | CRUD контрагентов |
| GET/POST/PUT/DELETE | /counterparties/{id}/contracts | Договоры |
| GET/POST/PUT/DELETE | /cascades | Каскады |
| GET | /cascades/active | Активный каскад |
| GET/PUT | /settings | Настройки |
| GET/POST/DELETE | /settings/tax | НДФЛ по годам |
| POST/GET/DELETE | /attachments | Вложения файлов |
