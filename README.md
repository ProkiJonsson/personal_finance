# Personal Finance Manager

A web application for managing personal finances: funds, accounts, hierarchical expense categories, and income/expense transactions.

## Tech Stack

**Backend:**

- FastAPI 0.115 + Uvicorn 0.30 — REST API with auto-documentation
- SQLAlchemy 2.0 — ORM, models in `backend/models.py`
- SQLite — database `backend/finance.db`
- JWT Authentication (python-jose + passlib[bcrypt]) — HS256, 24-hour tokens
- Pydantic 2.9 — request/response validation

**Frontend:**

- Vanilla HTML5 / CSS3 / JavaScript (ES6+) — no frameworks or bundlers
- Fetch API — backend communication
- localStorage/sessionStorage — JWT token storage

## Project Structure

```
finance/
├── backend/
│   ├── main.py              # FastAPI app, CORS, router setup
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # SQLite connection, sessions
│   ├── auth.py              # JWT logic, get_current_user dependency
│   ├── requirements.txt
│   ├── finance.db           # SQLite database
│   └── routers/
│       ├── auth.py          # /auth endpoints
│       ├── funds.py         # /funds CRUD
│       ├── accounts.py      # /accounts CRUD
│       ├── categories.py    # /categories CRUD (hierarchical)
│       └── transactions.py  # /transactions CRUD + filters
│
├── frontend/
│   ├── index.html           # Login / Registration
│   ├── dashboard.html       # Main dashboard with fund balances
│   ├── accounts.html        # Account management
│   ├── funds.html           # Fund management
│   ├── categories.html      # Category references (3 levels)
│   ├── operations.html      # Transactions list with filters
│   ├── css/style.css
│   └── js/app.js
│
└── README.md
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API runs on `http://127.0.0.1:8000`

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Frontend

Open `frontend/index.html` directly in a browser or serve via HTTP (optional):

```bash
# Simple Python HTTP server
python -m http.server 8080 --directory frontend
```

Then navigate to `http://localhost:8080`

## API Overview

**Base URL:** `http://127.0.0.1:8000`  
**Auth:** `Authorization: Bearer <JWT>`

| Endpoint Group   | Method | Path                 | Purpose                                                               |
| ---------------- | ------ | -------------------- | --------------------------------------------------------------------- |
| **Auth**         | POST   | `/auth/register`     | Register new user                                                     |
|                  | POST   | `/auth/login`        | User login                                                            |
| **Funds**        | GET    | `/funds`             | List funds                                                            |
|                  | POST   | `/funds`             | Create fund                                                           |
|                  | PUT    | `/funds/{id}`        | Update fund                                                           |
|                  | DELETE | `/funds/{id}`        | Delete fund                                                           |
| **Accounts**     | GET    | `/accounts`          | List accounts                                                         |
|                  | POST   | `/accounts`          | Create account                                                        |
|                  | PUT    | `/accounts/{id}`     | Update account                                                        |
|                  | DELETE | `/accounts/{id}`     | Delete account                                                        |
| **Categories**   | GET    | `/categories`        | List categories (filterable by type, parent)                          |
|                  | POST   | `/categories`        | Create category                                                       |
|                  | PUT    | `/categories/{id}`   | Update category                                                       |
|                  | DELETE | `/categories/{id}`   | Delete category                                                       |
| **Transactions** | GET    | `/transactions`      | List transactions (filterable by date, fund, account, category, type) |
|                  | POST   | `/transactions`      | Create transaction                                                    |
|                  | PUT    | `/transactions/{id}` | Update transaction                                                    |
|                  | DELETE | `/transactions/{id}` | Delete transaction                                                    |

Full endpoint documentation: `http://localhost:8000/docs`

## Frontend Status

| Page             | Status         | Features                                                          |
| ---------------- | -------------- | ----------------------------------------------------------------- |
| Login / Register | ✅ Ready       | Tab-based auth, remember me, auto-redirect                        |
| Dashboard        | ✅ Ready       | Fund cards with balances, last 10 transactions, loading skeletons |
| Funds            | ✅ Ready       | Full CRUD for funds (current/investment types)                    |
| Accounts         | ✅ Ready       | Full CRUD for accounts with balance management                    |
| Categories       | ✅ Ready       | 3-level hierarchical category management                          |
| Transactions     | ✅ Ready       | Full transaction list with advanced filters                       |
| Settings         | ❌ Not created |                                                                   |
| Profile          | ❌ Not created |                                                                   |

All pages include sidebar navigation.

## Key Architecture Decisions

**Funds vs Accounts:**

- **Fund** — logical budget unit (operational/investment). Required per transaction, represents financial activity type.
- **Account** — physical storage location (card, cash). Optional per transaction, represents where money is held.

**Category Hierarchy (4 levels):**

- **Level 4** — Activity types (root): Operational, Investment, Financial
- **Level 3** — Groups (parent = level 4)
- **Level 2** — Line items (parent = level 3)
- **Level 1** — Reserved

**Fund Balance:**

- Calculated on-the-fly as `SUM(income) - SUM(expenses)` from transactions (not stored in DB)
- Account balance stored as explicit field

**Database:**

- SQLite with no migrations — schema created via `SQLAlchemy.metadata.create_all()` on startup
- Delete `backend/finance.db` and restart to reset DB

**Authentication:**

- JWT tokens without refresh mechanism
- 24-hour expiration → re-login required
- CORS enabled for all origins (local dev only; restrict in production)

## Requirements

- Python 3.8+
- pip or conda for dependency management
- Modern browser supporting ES6+ JavaScript

See [backend/requirements.txt](backend/requirements.txt) for Python dependencies.
