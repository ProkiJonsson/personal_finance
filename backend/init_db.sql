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

CREATE TABLE IF NOT EXISTS counterparties (
    id          INTEGER      NOT NULL,
    user_id     INTEGER      NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contracts (
    id               INTEGER      NOT NULL,
    counterparty_id  INTEGER      NOT NULL,
    name             VARCHAR(255) NOT NULL DEFAULT 'Основной',
    description      TEXT,
    created_at       DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (counterparty_id) REFERENCES counterparties (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS funds (
    id          INTEGER      NOT NULL,
    user_id     INTEGER      NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    type        VARCHAR(20)  NOT NULL,
    contract_id INTEGER,
    is_archived BOOLEAN      NOT NULL DEFAULT 0,
    is_system   BOOLEAN      NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id)     REFERENCES users (id)     ON DELETE CASCADE,
    FOREIGN KEY (contract_id) REFERENCES contracts (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER      NOT NULL,
    user_id    INTEGER      NOT NULL,
    name       VARCHAR(255) NOT NULL,
    balance    FLOAT        NOT NULL DEFAULT 0.0,
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
    sort_order INTEGER      NOT NULL DEFAULT 0,
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
    fund_id     INTEGER,
    account_id  INTEGER,
    category_id INTEGER,
    comment     TEXT,
    is_initial  BOOLEAN  NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    CONSTRAINT ck_transactions_amount_positive CHECK (amount > 0),
    FOREIGN KEY (user_id)     REFERENCES users (id)       ON DELETE CASCADE,
    FOREIGN KEY (fund_id)     REFERENCES funds (id)       ON DELETE RESTRICT,
    FOREIGN KEY (account_id)  REFERENCES accounts (id)    ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories (id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS cascades (
    id             INTEGER  NOT NULL,
    user_id        INTEGER  NOT NULL,
    effective_from DATE     NOT NULL,
    created_at     DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cascade_slots (
    id            INTEGER NOT NULL,
    cascade_id    INTEGER NOT NULL,
    fund_id       INTEGER NOT NULL,
    target_amount FLOAT   NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    FOREIGN KEY (cascade_id) REFERENCES cascades (id) ON DELETE CASCADE,
    FOREIGN KEY (fund_id)    REFERENCES funds (id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS split_rules (
    id               INTEGER NOT NULL,
    cascade_id       INTEGER NOT NULL,
    trigger_position INTEGER,
    target_fund_id   INTEGER NOT NULL,
    percentage       FLOAT   NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_split_rules_percentage CHECK (percentage > 0 AND percentage <= 1),
    FOREIGN KEY (cascade_id)     REFERENCES cascades (id) ON DELETE CASCADE,
    FOREIGN KEY (target_fund_id) REFERENCES funds (id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tax_settings (
    id                  INTEGER  NOT NULL,
    user_id             INTEGER  NOT NULL,
    year                INTEGER  NOT NULL,
    tax_free_threshold  FLOAT    NOT NULL,
    rate_standard       FLOAT    NOT NULL DEFAULT 0.13,
    rate_elevated       FLOAT    NOT NULL DEFAULT 0.15,
    elevated_threshold  FLOAT    NOT NULL DEFAULT 2000000.0,
    created_at          DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    UNIQUE (user_id, year),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_settings (
    id                       INTEGER NOT NULL,
    user_id                  INTEGER NOT NULL,
    fund_accounting_enabled  BOOLEAN NOT NULL DEFAULT 0,
    max_attachment_size_mb   INTEGER NOT NULL DEFAULT 10,
    PRIMARY KEY (id),
    UNIQUE (user_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attachments (
    id          INTEGER      NOT NULL,
    user_id     INTEGER      NOT NULL,
    entity_type VARCHAR(20)  NOT NULL,
    entity_id   INTEGER      NOT NULL,
    filename    VARCHAR(255) NOT NULL,
    filepath    VARCHAR(500) NOT NULL,
    mime_type   VARCHAR(100) NOT NULL,
    size_bytes  INTEGER      NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- ── Индексы ───────────────────────────────────────────────────

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email          ON users (email);
CREATE INDEX IF NOT EXISTS        ix_users_id             ON users (id);

CREATE INDEX IF NOT EXISTS        ix_counterparties_id       ON counterparties (id);
CREATE INDEX IF NOT EXISTS        ix_counterparties_user_id  ON counterparties (user_id);

CREATE INDEX IF NOT EXISTS        ix_contracts_id               ON contracts (id);
CREATE INDEX IF NOT EXISTS        ix_contracts_counterparty_id  ON contracts (counterparty_id);

CREATE INDEX IF NOT EXISTS        ix_funds_id             ON funds (id);
CREATE INDEX IF NOT EXISTS        ix_funds_user_id        ON funds (user_id);
CREATE INDEX IF NOT EXISTS        ix_funds_contract_id    ON funds (contract_id);

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

CREATE INDEX IF NOT EXISTS        ix_cascades_id          ON cascades (id);
CREATE INDEX IF NOT EXISTS        ix_cascades_user_id     ON cascades (user_id);

CREATE INDEX IF NOT EXISTS        ix_cascade_slots_id         ON cascade_slots (id);
CREATE INDEX IF NOT EXISTS        ix_cascade_slots_cascade_id ON cascade_slots (cascade_id);
CREATE INDEX IF NOT EXISTS        ix_cascade_slots_fund_id    ON cascade_slots (fund_id);

CREATE INDEX IF NOT EXISTS        ix_split_rules_id          ON split_rules (id);
CREATE INDEX IF NOT EXISTS        ix_split_rules_cascade_id  ON split_rules (cascade_id);

CREATE INDEX IF NOT EXISTS        ix_tax_settings_id       ON tax_settings (id);
CREATE INDEX IF NOT EXISTS        ix_tax_settings_user_id  ON tax_settings (user_id);

CREATE INDEX IF NOT EXISTS        ix_app_settings_id       ON app_settings (id);
CREATE INDEX IF NOT EXISTS        ix_app_settings_user_id  ON app_settings (user_id);

CREATE INDEX IF NOT EXISTS        ix_attachments_id          ON attachments (id);
CREATE INDEX IF NOT EXISTS        ix_attachments_user_id     ON attachments (user_id);
CREATE INDEX IF NOT EXISTS        ix_attachments_entity      ON attachments (entity_type, entity_id);
