TAG_METADATA = [
    {
        "name": "Tender | v1",
        "description": "Операции с тендером v1.",
    },
    {
        "name": "healthz",
        "description": "Стандартная проверка работоспособности.",
    },
]

TITLE = "Tracking Outcomes Tenders"
DESCRIPTION = (
    "Микросервис трекинга статуса тендеров.\n\n"
    "Реализован на FastAPI по шаблону луковой архитектуры "
    "(https://github.com/Uoiferise/fastapi-onion-architecture)."
)
VERSION = "0.1.0"

ERRORS_MAP = {
    "postgres": "Не удалось подключиться к PostgreSQL",
    "rabbit": "Не удалось подключиться к RabbitMQ",
}
