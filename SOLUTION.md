# Tracking Outcomes Tenders — логика и алгоритм работы приложения

Микросервис трекинга статуса тендеров на **FastAPI** по шаблону **луковой
архитектуры** (onion architecture). Каждое изменение статуса тендера:

1. фиксируется в таблице истории `tender_status_history`;
2. публикуется событием в **RabbitMQ** для внешних потребителей.

Документ описывает, как устроено приложение «изнутри»: архитектурные слои,
поток данных, алгоритмы каждого сценария и логику ключевых компонентов.

---

## Оглавление

1. [Архитектура](#архитектура)
2. [Слои приложения](#слои-приложения)
3. [Доменная модель](#доменная-модель)
4. [Сценарии (алгоритмы)](#сценарии)
   - [Создание тендера](#сценарий-создание-тендера)
   - [Изменение статуса](#сценарий-изменение-статуса)
   - [Получение тендера с историей](#сценарий-получение-тендера)
   - [Получение истории статусов](#сценарий-получение-истории)
   - [Healthcheck](#сценарий-healthcheck)
5. [Поток данных (диаграмма)](#поток-данных)
6. [Ключевые механизмы](#ключевые-механизмы)
   - [Unit of Work и транзакции](#unit-of-work)
   - [Репозитории](#репозитории)
   - [Сериализация моделей](#сериализация)
   - [Публикация в RabbitMQ](#rabbitmq-логика)
   - [Консюмер событий](#консюмер)
7. [Формат ответов и ошибки](#ответы-и-ошибки)
8. [Тестирование логики](#тестирование-логики)
   - [Окружение тестов](#окружение-тестов)
   - [Структура тестов](#структура-тестов)
   - [Проверка сценариев](#проверка-сценариев)
   - [Ключевые механизмы тестов](#ключевые-механизмы-тестов)

---

## Архитектура

Проект построен по **луковой архитектуре**: внешние интерфейсы (HTTP, брокер)
находятся на периферии, бизнес-логика — в центре. Зависимости направлены
«внутрь»: роутер → сервис → репозиторий → БД.

```
        HTTP (FastAPI)
             │
             ▼
     ┌───────────────┐
     │  Router (API) │   валидация входа/выхода, HTTP-коды
     └───────────────┘
             │
             ▼
     ┌───────────────┐
     │  Service      │   бизнес-логика, транзакции, правила статусов
     └───────────────┘
        │        │
        ▼        ▼
  ┌────────┐ ┌────────┐
  │ Repo   │ │ Broker │   доступ к БД и публикация событий
  └────────┘ └────────┘
        │
        ▼
   PostgreSQL / RabbitMQ
```

Внутренние инфраструктурные слои (`utils/`, `models/`, `schemas/`)
используются всеми уровнями.

---

## Слои приложения

| Слой | Каталог | Ответственность |
|---|---|---|
| API (роутеры) | `src/api/v1/routers/` | HTTP-эндпоинты, DI, HTTP-коды |
| Сервисы | `src/api/v1/services/` | Бизнес-логика, транзакции, RabbitMQ |
| Репозитории | `src/repositories/` | SQL-запросы к БД |
| Модели | `src/models/` | ORM-модели SQLAlchemy |
| Схемы | `src/schemas/` | Pydantic-модели (вход/выход API) |
| Инфраструктура | `src/utils/` | `UnitOfWork`, базовые сервис/репозиторий, константы |
| Брокер | `src/broker/` | Подключение, producer, consumer RabbitMQ |
| БД | `src/database/` | Движок и фабрика сессий SQLAlchemy |
| Конфигурация | `src/config.py` | Настройки из `.env` |

---

## Доменная модель

**Тендер** (`TenderModel`, таблица `tender`):

- `id` — UUID (PK, генерируется на стороне Python через `uuid4`);
- `title` — название (обязательное, до 255 символов);
- `description` — описание (опционально);
- `status` — текущий статус (`draft` по умолчанию);
- `customer` — заказчик (опционально);
- `created_at` / `updated_at` — временные метки, заполняются СУБД
  (`server_default`).

**История статуса** (`TenderStatusHistoryModel`, таблица `tender_status_history`):

- `id` — UUID (PK);
- `tender_id` — FK на `tender.id` (каскадное удаление);
- `old_status` — статус «до» (`None` для первичной записи);
- `new_status` — статус «после»;
- `changed_by` — кто изменил;
- `reason` — причина изменения;
- `created_at` — когда изменили;
- связь `tender.status_history` — список записей истории (order by `created_at`).

**Статусы** (`TenderStatus` в `src/utils/constants.py`):

`draft` → `active` → `won` | `lost`

Каждый переход статуса — отдельная строка в истории. Изменение статуса на
текущий запрещено (HTTP `400`).

---

## Сценарии (алгоритмы)

### Сценарий: Создание тендера

`POST /api/v1/tender/`

1. **Роутер** (`tender.py:26`): FastAPI валидирует тело запроса по
   `CreateTenderRequest` (`title` обязателен, 1–255 символов).
2. Роутер внедряет `TenderService` через `Depends()` — создаётся `UnitOfWork`.
3. **Сервис** `create_tender` (`tender.py:31`):
   - выполняется в декораторе `@transaction_mode(auto_flush=True)`;
   - открывается транзакция UoW;
   - через репозиторий `add_one_and_get_obj` выполняется
     `INSERT ... RETURNING` — тендер создаётся со статусом `draft`,
     возвращается объект с заполненным `id` и временными метками;
   - создаётся первая запись истории `TenderStatusHistoryModel`
     (`old_status=None`, `new_status="draft"`, `changed_by="system"`,
     `reason="Тендер создан"`) и добавляется в сессию;
   - в RabbitMQ публикуется событие о создании;
   - возвращается `created_tender.to_schema()` — `TenderDB`.
4. **Роутер** оборачивает результат в `CreateTenderResponse` (HTTP `201`).

### Сценарий: Изменение статуса

`PATCH /api/v1/tender/{tender_id}/status`

1. **Роутер** (`tender.py:54`): валидация `UpdateTenderStatusRequest`
   (`new_status` из enum `TenderStatus`, `changed_by` обязателен, `reason` — нет).
2. **Сервис** `update_tender_status` (`tender.py:73`), `@transaction_mode(auto_flush=True)`:
   - поиск тендера по `id` через репозиторий `get_by_filter_one_or_none`;
     если не найден → `HTTP 404` («Тендер не найден»);
   - сравнение `old_status` с `new_status`: если равны →
     `HTTP 400` («Статус тендера не изменился»);
   - обновление статуса тендера: `update_one_by_id` (`UPDATE ... RETURNING`);
   - создание объекта `TenderStatusHistoryModel`
     (`old_status`, `new_status`, `changed_by`, `reason`);
   - добавление в сессию `session_add` + **`flush()`** — flush применяет
     Python-дефолт `id` (uuid4) и возвращает из БД `created_at`
     (server_default через RETURNING); только после этого запись имеет
     полный набор полей;
   - публикация события в RabbitMQ;
   - перечитывание тендера с историей через `get_tender_with_history`;
   - добавление свежей записи `history.to_schema()` к списку истории ответа;
   - возврат `TenderWithHistory`.
3. **Роутер** оборачивает в `TenderResponse` (HTTP `200`).

### Сценарий: Получение тендера с историей

`GET /api/v1/tender/{tender_id}`

1. **Сервис** `get_tender_with_history` (`tender.py:56`), `@transaction_mode`:
   - репозиторий `get_tender_with_history` выполняет `SELECT` с
     `selectinload(status_history)` — тендер подтягивается вместе со всей
     историей статусов одним запросом (без N+1);
   - если тендера нет → `HTTP 404`;
   - каждая запись истории сериализуется через `entry.to_schema()`;
   - возвращается `TenderWithHistory`.
2. **Роутер** оборачивает в `TenderResponse` (HTTP `200`).

### Сценарий: Получение истории статусов

`GET /api/v1/tender/{tender_id}/status-history`

1. **Сервис** `get_tender_status_history` (`tender.py:117`), `@transaction_mode`:
   - тот же запрос с `selectinload` (переиспользуется репозиторий);
   - если тендера нет → `HTTP 404`;
   - возвращается список `list[TenderStatusHistoryDB]` (все записи истории).
2. **Роутер** оборачивает в `TenderStatusHistoryResponse` (HTTP `200`).

### Сценарий: Healthcheck

`GET /api/healthz/`

1. В `src/api/__init__.py:28` параллельно (`asyncio.gather`) проверяются:
   - **PostgreSQL**: `SELECT 1`;
   - **RabbitMQ**: `check_connection()` (подключение с таймаутом 2 с).
2. Любая ошибка → `HTTP 400` с текстом из `ERRORS_MAP`.
3. Успех → `BaseResponse` (HTTP `200`).

---

## Поток данных

```
Клиент (curl / Swagger)
   │  POST /api/v1/tender/                PATCH /api/v1/tender/{id}/status
   ▼                                       ▼
Router ── валидация Pydantic ── Service ── UnitOfWork (транзакция)
                                              │
                                              ├── Repo: INSERT/UPDATE/SELECT
                                              │         │
                                              │         ▼
                                              │    PostgreSQL
                                              │         │
                                              │    tenders + tender_status_history
                                              │
                                              └── Producer ──► RabbitMQ (topic "tenders",
                                                                   key "tender.status.changed")
                                                                         │
                                                                         ▼
                                                                  Consumer ──► loguru (логи)
```

---

## Ключевые механизмы

### Unit of Work

`src/utils/unit_of_work.py` — центральный механизм транзакций.

- `UnitOfWork` открывает сессию (`async_session_maker`) и создаёт репозитории
  `tender` и `tender_status_history` при входе в контекст (`async with self.uow`).
- На выходе без ошибок — `commit()`; при исключении — `rollback()`.
- Методы:
  - `flush()` — отправка pending-изменений в БД;
  - `session_add(obj)` — добавление объекта в сессию;
  - `session_refresh(obj)` — перезагрузка объекта из БД.

**Важно про `autoflush=False`** (`src/database/db.py:27`): сессия не сбрасывает
изменения автоматически перед запросами. Поэтому новые объекты (история
статуса) до явного `flush()` не имеют значений `id`/`created_at` —
их возвращает БД при записи. Это причина явного `flush()` в
`update_tender_status`.

### Декоратор `transaction_mode`

`src/utils/service.py:24`:

- если UoW ещё не открыт — оборачивает вызов в `async with self.uow:`;
- если уже открыт (вложенный вызов сервиса) — выполняет функцию как есть;
- при `auto_flush=True` выполняет `flush()` **после** возврата из функции.
  Это важно: автофлаш не влияет на операции внутри самой функции —
  поэтому явные `flush()` ставятся там, где нужны свежие значения полей.

### Репозитории

`src/utils/repository.py` — `SqlAlchemyRepository` (generic по модели).
Базовые операции используют Core-выражения с `RETURNING`:

- `add_one_and_get_obj` → `INSERT ... RETURNING` (возвращает объект с
  `id`/метками);
- `update_one_by_id` → `UPDATE ... RETURNING`;
- `get_by_filter_one_or_none` → `SELECT ... LIMIT 1`;
- `get_by_filter_all` → все записи по фильтру;
- `delete_*` → удаление по фильтру/списку/все.

`TenderRepository` (`src/repositories/tender.py`) добавляет
`get_tender_with_history` с `selectinload` для подгрузки связи истории.

### Сериализация

ORM-модель конвертируется в Pydantic-схему через метод `to_schema()`:

```python
def to_schema(self) -> TenderStatusHistoryDB:
    return TenderStatusHistoryDB(**self.__dict__)
```

`self.__dict__` содержит атрибуты SQLAlchemy-объекта. Для корректной
валидации обязательных полей (`id`, `created_at`) объект должен быть
**зафлашен** (записан в БД) — иначе эти поля отсутствуют.

### RabbitMQ

**Producer** (`src/broker/producer.py`):
- формирует JSON-сообщение:
  `tender_id, old_status, new_status, changed_by, reason, changed_at`;
- публикует в топик-обмен `tenders` (durable) с routing key
  `tender.status.changed` в очередь `tender_status_updates` (durable);
- `delivery_mode=PERSISTENT` — сообщение переживает перезапуск брокера;
- **отказоустойчивость**: любые ошибки брокера перехватываются
  (`try/except`), логируются через `loguru` и НЕ прерывают запрос —
  запись в БД уже сохранена (eventual consistency: БД — источник истины,
  RabbitMQ — асинхронное уведомление).

**Connection** (`src/broker/connection.py`):
- `connect_robust` — надёжное соединение с авто-переподключением;
- при первом подключении объявляются exchange (TOPIC, durable), очередь
  (durable) и биндинг;
- соединение переиспользуется (синглтон `rabbitmq_connection`).

### Консюмер

`src/broker/consumer.py` — отдельный процесс (`python -m src.broker.consumer`):

- подключается к той же очереди;
- `prefetch_count=1` — по одному сообщению за раз;
- получает сообщения через `queue.iterator()` и логирует их содержимое;
- `message.process()` подтверждает обработку (ack) — при сбое сообщение
  вернётся в очередь.

---

## Ответы и ошибки

Единый формат ответа (`src/schemas/response.py`):

```json
{
  "status": 200,
  "error": false,
  "payload": { "...": "данные" }
}
```

| Код | Сценарий |
|---|---|
| `201` | Создание тендера |
| `200` | Чтение, изменение статуса, история |
| `400` | Статус не изменился; сбой healthcheck |
| `404` | Тендер не найден |

---

## Тестирование логики

Приложение покрыто **интеграционными тестами**: они проверяют все описанные
выше сценарии на трёх уровнях — репозиторий, сервис, роутер. RabbitMQ в
тестах не используется: публикация подменяется фейком.

### Окружение тестов

- Запуск: `uv run pytest` при `MODE=TEST`.
- Тестовая БД создаётся автоматически фикстурой `create_test_db`
  (`tests/conftest.py`) и **удаляется** после завершения сессии тестов.
- Схема пересоздаётся каждый сеанс фикстурой `setup_db`
  (`drop_all` + `create_all`).
- Каждый тест выполняется в **отдельной транзакции** (фикстура
  `transaction_session`): изменения откатываются в конце теста, поэтому
  тесты полностью изолированы друг от друга.
- Тестовые данные загружаются фикстурами `setup_tenders` и
  `setup_tender_status_history` из `tests/fixtures/db_mocks/`.

### Структура тестов

| Файл | Что проверяет |
|---|---|
| `tests/integration/utils/test_repository.py` | CRUD `TenderRepository` и `TenderStatusHistoryRepository`, `get_tender_with_history` |
| `tests/integration/utils/test_service.py` | Бизнес-логика `TenderService` и `BaseService` |
| `tests/integration/api/v1/routers/test_tender_router.py` | HTTP-эндпоинты: коды ответа, валидация, сериализация |
| `tests/fixtures/db_mocks/tenders.py` | Данные-моки: 3 тендера (`draft`/`active`/`won`) и история статусов |
| `tests/fixtures/testing_cases/` | Параметры для `@pytest.mark.parametrize` (`BaseTestCase`, `RequestTestCase`) |
| `tests/fixtures/__init__.py` | `FakeProducer`, `FakeUnitOfWork`, `FakeBaseService` |

### Проверка сценариев

- **Создание тендера** — роутер: `201` для валидного тела, `422` для
  пустого/отсутствующего/слишком длинного `title`; сервис: новый тендер имеет
  статус `draft`, в БД ровно 1 запись, опубликовано ровно 1 событие.
- **Изменение статуса** — роутер: `200` (успех), `400` (тот же статус),
  `404` (нет тендера), `422` (невалидный `new_status`); сервис: статус
  обновлён на `active`, история выросла (проверяется `len(result.status_history)`),
  опубликовано событие в `FakeProducer`.
- **Получение тендера с историей / истории статусов** — репозиторий:
  подтягивается связь `status_history` без N+1; сервис: корректно
  сериализуются записи; роутер: `200`, `404`, `422`.
- **Тесты `update_one_by_id`** — проверяют, что `UPDATE ... RETURNING`
  возвращает объект с новыми значениями.

### Ключевые механизмы тестов

- **`FakeUnitOfWork`** (`tests/fixtures/__init__.py:30`) — наследник
  `UnitOfWork`, работающий на переданной `transaction_session` вместо
  `async_session_maker`; репозитории создаются из той же сессии.
- **`FakeProducer`** — перехватывает вызовы `publish_tender_status_change` в
  список `published`; подменяется через
  `monkeypatch.setattr("src.api.v1.services.tender.producer", ...,
  raising=False)`. Факт публикации проверяется
  (`fake_producer.published`), реальный брокер не требуется.
- **`FakeBaseService`** — базовый сервис, привязанный к `FakeUnitOfWork`,
  для тестирования наследуемых CRUD-операций `BaseService`.