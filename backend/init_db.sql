-- ============================================================
-- Finance App — инициализация базы данных
-- Используется при первом развёртывании на сервере.
-- Выполнить: sqlite3 finance.db < init_db.sql
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Таблицы ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER      NOT NULL,
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS funds (
    id         INTEGER      NOT NULL,
    user_id    INTEGER      NOT NULL,
    name       VARCHAR(255) NOT NULL,
    type       VARCHAR(10)  NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER      NOT NULL,
    user_id    INTEGER      NOT NULL,
    name       VARCHAR(255) NOT NULL,
    balance    FLOAT        NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS categories (
    id         INTEGER      NOT NULL,
    user_id    INTEGER      NOT NULL,
    name       VARCHAR(255) NOT NULL,
    type       VARCHAR(7),
    level      INTEGER      NOT NULL,
    parent_id  INTEGER,
    sort_order INTEGER      NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    CONSTRAINT ck_categories_level CHECK (level >= 1 AND level <= 4),
    FOREIGN KEY (user_id)   REFERENCES users (id)       ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES categories (id)  ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER  NOT NULL,
    user_id     INTEGER  NOT NULL,
    date        DATETIME NOT NULL,
    amount      FLOAT    NOT NULL,
    type        VARCHAR(7) NOT NULL,
    fund_id     INTEGER  NOT NULL,
    account_id  INTEGER,
    category_id INTEGER,
    comment     TEXT,
    is_initial  BOOLEAN  NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    CONSTRAINT ck_transactions_amount_positive CHECK (amount > 0),
    FOREIGN KEY (user_id)     REFERENCES users (id)       ON DELETE CASCADE,
    FOREIGN KEY (fund_id)     REFERENCES funds (id)       ON DELETE RESTRICT,
    FOREIGN KEY (account_id)  REFERENCES accounts (id)    ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id)  ON DELETE RESTRICT
);

-- ── Индексы ───────────────────────────────────────────────────

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email          ON users (email);
CREATE INDEX IF NOT EXISTS        ix_users_id             ON users (id);

CREATE INDEX IF NOT EXISTS        ix_funds_id             ON funds (id);
CREATE INDEX IF NOT EXISTS        ix_funds_user_id        ON funds (user_id);

CREATE INDEX IF NOT EXISTS        ix_accounts_id          ON accounts (id);
CREATE INDEX IF NOT EXISTS        ix_accounts_user_id     ON accounts (user_id);

CREATE INDEX IF NOT EXISTS        ix_categories_id        ON categories (id);
CREATE INDEX IF NOT EXISTS        ix_categories_user_id   ON categories (user_id);
CREATE INDEX IF NOT EXISTS        ix_categories_parent_id ON categories (parent_id);

CREATE INDEX IF NOT EXISTS        ix_transactions_id          ON transactions (id);
CREATE INDEX IF NOT EXISTS        ix_transactions_user_id     ON transactions (user_id);
CREATE INDEX IF NOT EXISTS        ix_transactions_date        ON transactions (date);
CREATE INDEX IF NOT EXISTS        ix_transactions_fund_id     ON transactions (fund_id);
CREATE INDEX IF NOT EXISTS        ix_transactions_account_id  ON transactions (account_id);
CREATE INDEX IF NOT EXISTS        ix_transactions_category_id ON transactions (category_id);
