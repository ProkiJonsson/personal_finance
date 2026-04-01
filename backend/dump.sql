-- SQLite Database Dump
-- Generated from finance.db


-- Table: accounts
CREATE TABLE accounts (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	balance FLOAT NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Data (2 rows):
INSERT INTO accounts (id, user_id, name, balance, created_at) VALUES (1, 1, 'Наличка', 0.0, '2026-03-30 06:17:40');
INSERT INTO accounts (id, user_id, name, balance, created_at) VALUES (2, 1, 'Тбанк карта', 0.0, '2026-03-30 06:21:02');


-- Table: categories
CREATE TABLE categories (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	type VARCHAR(7), 
	level INTEGER NOT NULL, 
	parent_id INTEGER, 
	sort_order INTEGER NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_categories_level CHECK (level >= 1 AND level <= 4), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(parent_id) REFERENCES categories (id) ON DELETE SET NULL
);

-- Data (34 rows):
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (3, 1, 'Операционная деятельность', NULL, 4, NULL, 0, '2026-03-30 09:52:57');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (4, 1, 'Инвестиционная деятельность', NULL, 4, NULL, 10, '2026-03-30 09:53:08');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (5, 1, 'Финансовая деятельность', NULL, 4, NULL, 20, '2026-03-30 10:42:07');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (6, 1, 'Доход от бизнеса', 'income', 3, 3, 0, '2026-03-30 10:42:54');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (8, 1, 'Прочие доходы', 'income', 3, 3, 10, '2026-03-30 11:08:52');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (9, 1, 'Доход от МП', 'income', 2, 6, 10, '2026-03-30 11:30:08');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (10, 1, 'Доход от прочих проектов', 'income', 2, 6, 0, '2026-03-30 11:30:22');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (11, 1, 'Доход от наставничества и коучинга', 'income', 2, 6, 20, '2026-03-30 11:30:33');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (12, 1, 'Кеш бэк', 'income', 2, 8, 0, '2026-03-30 11:31:12');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (13, 1, 'Социальные выплаты', 'income', 2, 8, 10, '2026-03-30 11:31:23');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (14, 1, 'Прочие доходы', 'income', 2, 8, 20, '2026-03-30 11:31:33');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (15, 1, 'Текущие расходы на жилье', 'expense', 3, 3, 40, '2026-03-30 11:31:58');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (16, 1, 'Коммунальные платежи', 'expense', 2, 15, 0, '2026-03-30 11:32:13');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (17, 1, 'Расходы на ГТС, Интернет и кабельное телевидение', 'expense', 2, 15, 20, '2026-03-30 11:32:39');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (19, 1, 'Приобретение мелкой бытовой техники', 'expense', 2, 15, 30, '2026-03-30 11:33:25');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (20, 1, 'Прочие расходы на жилье', 'expense', 2, 15, 50, '2026-03-30 11:33:35');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (21, 1, 'Аренда жилья', 'expense', 2, 15, 40, '2026-03-30 11:33:43');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (22, 1, 'Текущий ремонт и хозрасходы', 'expense', 2, 15, 10, '2026-03-30 11:34:06');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (23, 1, 'Компенсация расходов', 'expense', 3, 3, 20, '2026-03-30 12:02:35');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (24, 1, 'Расходы супруги', 'expense', 2, 23, 0, '2026-03-30 12:03:00');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (25, 1, 'Продукты питания', 'expense', 3, 3, 30, '2026-03-30 12:03:26');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (26, 1, 'Дети', 'expense', 3, 3, 60, '2026-03-30 12:04:29');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (28, 1, 'Праздники детям, ДР, подарки', 'expense', 2, 26, 10, '2026-03-30 12:09:43');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (30, 1, 'Одежда детям', 'expense', 2, 26, 20, '2026-03-30 12:11:20');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (31, 1, 'Лечение детей', 'expense', 2, 26, 30, '2026-03-30 12:11:27');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (32, 1, 'Карманные расходы детей', 'expense', 2, 26, 40, '2026-03-30 12:11:37');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (33, 1, 'Кино, театр, концерт, развлечения для детей', 'expense', 2, 26, 50, '2026-03-30 12:11:45');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (34, 1, 'Прочие расходы на детей', 'expense', 2, 26, 60, '2026-03-30 12:11:53');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (35, 1, 'Кафе, ресторан, продукты, снеки для детей', 'expense', 2, 26, 70, '2026-03-30 12:12:00');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (36, 1, 'Книги, конструкторы ... детям', 'expense', 2, 26, 80, '2026-03-30 12:12:27');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (37, 1, 'Транспортные расходы детей, такси', 'expense', 2, 26, 90, '2026-03-30 12:12:50');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (38, 1, 'Обучение, развитие и спорт детей', 'expense', 2, 26, 0, '2026-03-30 12:32:09');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (39, 1, 'Игрушки и питомцы', NULL, 2, 26, 100, '2026-03-30 12:59:00');
INSERT INTO categories (id, user_id, name, type, level, parent_id, sort_order, created_at) VALUES (40, 1, 'Автомобиль', 'expense', 3, 3, 70, '2026-03-30 13:01:21');


-- Table: funds
CREATE TABLE funds (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	type VARCHAR(10) NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Data (4 rows):
INSERT INTO funds (id, user_id, name, type, created_at) VALUES (1, 1, 'Фонд текущих расходов', 'current', '2026-03-30 06:20:31');
INSERT INTO funds (id, user_id, name, type, created_at) VALUES (2, 1, 'Я', 'current', '2026-03-30 06:40:35');
INSERT INTO funds (id, user_id, name, type, created_at) VALUES (3, 1, 'Отдых', 'current', '2026-03-30 06:40:44');
INSERT INTO funds (id, user_id, name, type, created_at) VALUES (4, 1, 'Резервный фонд', 'current', '2026-03-30 06:41:02');


-- Table: transactions
CREATE TABLE transactions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATETIME NOT NULL, 
	amount FLOAT NOT NULL, 
	type VARCHAR(7) NOT NULL, 
	fund_id INTEGER NOT NULL, 
	account_id INTEGER, 
	category_id INTEGER, 
	comment TEXT, 
	is_initial BOOLEAN NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_transactions_amount_positive CHECK (amount > 0), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(fund_id) REFERENCES funds (id) ON DELETE RESTRICT, 
	FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL, 
	FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT
);

-- Data (4 rows):
INSERT INTO transactions (id, user_id, date, amount, type, fund_id, account_id, category_id, comment, is_initial, created_at) VALUES (1, 1, '2026-01-01 00:00:00.000000', 11.0, 'income', 1, 1, NULL, NULL, 1, '2026-03-30 06:42:55');
INSERT INTO transactions (id, user_id, date, amount, type, fund_id, account_id, category_id, comment, is_initial, created_at) VALUES (2, 1, '2026-01-01 00:00:00.000000', 11.0, 'income', 2, 1, NULL, NULL, 1, '2026-03-30 06:42:55');
INSERT INTO transactions (id, user_id, date, amount, type, fund_id, account_id, category_id, comment, is_initial, created_at) VALUES (3, 1, '2026-01-01 00:00:00.000000', 11.0, 'income', 3, 1, NULL, NULL, 1, '2026-03-30 06:42:55');
INSERT INTO transactions (id, user_id, date, amount, type, fund_id, account_id, category_id, comment, is_initial, created_at) VALUES (4, 1, '2026-01-01 00:00:00.000000', 11.0, 'income', 4, 1, NULL, NULL, 1, '2026-03-30 06:42:55');


-- Table: users
CREATE TABLE users (
	id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

-- Data (1 rows):
INSERT INTO users (id, name, email, password_hash, created_at) VALUES (1, 'Рашид', 'rashid@test.com', '$2b$12$9I8U5NaC3RXL66cA.j2m/Oz4EkcycOiodQvQZwkLA7ZEDMf4Y1dHm', '2026-03-30 06:16:23');

