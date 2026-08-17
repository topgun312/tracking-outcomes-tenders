# Tracking Outcomes Tenders

Микросервис трекинга статуса тендеров на **FastAPI**, реализованный по шаблону **луковой архитектуры**
(на базе [fastapi-onion-architecture](https://github.com/Uoiferise/fastapi-onion-architecture)).

Каждое изменение статуса тендера фиксируется в отдельной таблице истории
(кто изменил, когда и почему) и дополнительно публикуется в **RabbitMQ**.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-FB3C01?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)

## Содержание
1) [Быстрый старт](#quick-start)
2) [Статусы тендера](#tender-statuses)
3) [API](#api)
4) [RabbitMQ](#rabbitmq)
5) [Линтеры](#linters)
6) [Структура проекта](#project-structure)

## <a id="quick-start">Быстрый старт</a> 🚀

Управление зависимостями — **uv** (см. [pyproject.toml](pyproject.toml)).

```bash
# Установить окружение
uv sync

# Настроить переменные окружения
cp .env.example .env
```

### Переменные окружения
**.env**
```dotenv
MODE=DEV

DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=postgres
DB_NAME=tracking_outcomes_tenders

RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASS=guest
RABBITMQ_VHOST=/
RABBITMQ_EXCHANGE=tenders
RABBITMQ_STATUS_QUEUE=tender_status_updates
```

### Миграции (Alembic)
```bash
uv run alembic upgrade head        # применить миграции
uv run alembic downgrade -1        # откатить на одну миграцию
uv run alembic revision --autogenerate -m 'message'   # новая миграция
```

### Запуск приложения
```bash
# API (Swagger на http://127.0.0.1:8000/docs)
uv run uvicorn src.main:app --reload

# либо: python -m src
```

### Запуск консюмера (логирование событий из RabbitMQ)
```bash
uv run python -m src.broker.consumer
```

## <a id="tender-statuses">Статусы тендера</a> 📌

| Значение (enum) | Статус |
|---|---|
| `draft` | Черновик |
| `active` | Активен |
| `won` | Выигран |
| `lost` | Проигран |

Каждый переход статуса сохраняется в таблицу `tender_status_history`:
`old_status`, `new_status`, `changed_by` (кто), `created_at` (когда), `reason` (почему).
Изменение статуса на текущий возвращает `400 Bad Request`.

## <a id="api">API</a> 🔌

Базовый префикс: `/api/v1`

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/tender/` | Создать тендер (стартовый статус — `draft`) |
| `GET` | `/tender/{tender_id}` | Получить тендер вместе с историей статусов |
| `PATCH` | `/tender/{tender_id}/status` | Изменить статус (`new_status`, `changed_by`, `reason`) |
| `GET` | `/tender/{tender_id}/status-history` | Получить историю статусов тендера |
| `GET` | `/api/healthz/` | Проверка подключения к PostgreSQL и RabbitMQ |

### Примеры

**Создание тендера**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/tender/ \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Поставка оборудования",
    "description": "Закупка серверов",
    "customer": "ООО Ромашка"
  }'
```

**Изменение статуса**
```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/tender/{tender_id}/status \
  -H 'Content-Type: application/json' \
  -d '{
    "new_status": "active",
    "changed_by": "ivanov",
    "reason": "Тендер опубликован"
  }'
```

## <a id="rabbitmq">RabbitMQ</a> 🐇

События изменения статуса публикуются в топик-обмен `tenders`
с routing key `tender.status.changed` в очередь `tender_status_updates` (durable).

Формат сообщения (JSON):
```json
{
  "tender_id": "…",
  "old_status": "draft",
  "new_status": "active",
  "changed_by": "ivanov",
  "reason": "Тендер опубликован",
  "changed_at": "2026-08-16T00:00:00+00:00"
}
```

Если брокер недоступен, событие не теряется для бизнес-логики:
запись сохраняется в БД, а ошибка публикации логируется через `loguru`
(запрос не прерывается).

## <a id="linters">Линтеры</a> 🧹

Используются **isort**, **black** и **flake8** (без ruff).

```bash
uv run isort --check-only src/ alembic/ && uv run isort src/ alembic/
uv run black --check src/ alembic/ && uv run black src/ alembic/
uv run flake8 src/ alembic/
```

Конфигурация: `[tool.black]` / `[tool.isort]` в [pyproject.toml](pyproject.toml), [.flake8](.flake8).

## <a id="project-structure">Структура проекта</a> 📂

```
.
├── alembic
│   ├── versions               # миграции БД
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── src
│   ├── api
│   │   └── v1
│   │       ├── routers        # HTTP-маршруты
│   │       └── services       # бизнес-логика
│   ├── broker
│   │   ├── connection.py      # подключение к RabbitMQ (exchange, очередь)
│   │   ├── constants.py       # константы брокера (routing key)
│   │   ├── consumer.py        # класс-консюмер событий RabbitMQ
│   │   └── producer.py        # класс-публикатор событий
│   ├── database
│   │   └── db.py              # движок и фабрика сессий SQLAlchemy
│   ├── models                 # ORM-модели
│   ├── repositories           # доступ к данным
│   ├── schemas                # Pydantic-схемы
│   ├── utils                  # repository, service, unit_of_work и др.
│   ├── config.py              # настройки из .env
│   ├── main.py                # создание FastAPI-приложения
│   ├── metadata.py            # метаданные Swagger
│   └── __main__.py            # запуск через `python -m src`
├── pyproject.toml             # зависимости и настройки uv/black/isort
├── .env.example
├── .flake8
└── .gitignore
```

### Как взаимодействуют компоненты
1) HTTP-запрос принимает роутер (`api/v1/routers/tender.py`).
2) Роутер вызывает сервис (`api/v1/services/tender.py`), где выполняется бизнес-логика.
3) Сервис работает с БД через репозиторий (`repositories/`) в рамках транзакции **Unit of Work**.
4) Изменение статуса сохраняется в `tender_status_history` и публикуется в RabbitMQ.
5) Результат сериализуется Pydantic-схемой (`schemas/`) и возвращается как JSON.