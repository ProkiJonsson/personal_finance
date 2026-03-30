# Личные финансы

Веб-приложение для учёта личных финансов.

## Стек

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** HTML / CSS / JavaScript (vanilla)

## Структура проекта

```
finance/
├── backend/
│   ├── main.py          # FastAPI приложение, маршруты
│   ├── database.py      # Подключение к SQLite, сессии
│   ├── models.py        # SQLAlchemy модели
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── README.md
```

## Запуск

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API будет доступен на `http://127.0.0.1:8000`.
Документация: `http://127.0.0.1:8000/docs`

### Frontend

Откройте `frontend/index.html` в браузере (или раздайте через любой статический сервер).

## API

| Метод  | Путь                 | Описание                |
| ------ | -------------------- | ----------------------- |
| GET    | `/transactions`      | Список транзакций       |
| POST   | `/transactions`      | Создать транзакцию      |
| DELETE | `/transactions/{id}` | Удалить транзакцию      |
| GET    | `/summary`           | Баланс, доходы, расходы |
