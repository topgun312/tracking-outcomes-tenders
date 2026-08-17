import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(".env"))


class Settings:
    MODE: str = os.environ.get("MODE", "DEV")

    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")
    DB_USER: str = os.environ.get("DB_USER", "postgres")
    DB_PASS: str = os.environ.get("DB_PASS", "postgres")
    DB_NAME: str = os.environ.get("DB_NAME", "tracking_outcomes_tenders")

    DB_URL: str = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    RABBITMQ_HOST: str = os.environ.get("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.environ.get("RABBITMQ_PORT", 5672))
    RABBITMQ_USER: str = os.environ.get("RABBITMQ_USER", "guest")
    RABBITMQ_PASS: str = os.environ.get("RABBITMQ_PASS", "guest")
    RABBITMQ_VHOST: str = os.environ.get("RABBITMQ_VHOST", "/")

    RABBITMQ_URL: str = (
        f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    )

    RABBITMQ_EXCHANGE: str = os.environ.get("RABBITMQ_EXCHANGE", "tenders")
    RABBITMQ_STATUS_QUEUE: str = os.environ.get(
        "RABBITMQ_STATUS_QUEUE", "tender_status_updates"
    )


settings = Settings()
