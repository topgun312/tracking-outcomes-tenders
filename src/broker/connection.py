import aio_pika
from aio_pika import Exchange, RobustChannel, RobustConnection
from aio_pika.abc import AbstractRobustChannel

from src.broker.constants import ROUTING_KEY_STATUS_CHANGED
from src.config import settings


class RabbitMQConnection:
    """Управляет подключением к RabbitMQ: соединение, канал, exchange и очередь."""

    def __init__(
        self,
        url: str = settings.RABBITMQ_URL,
        exchange_name: str = settings.RABBITMQ_EXCHANGE,
        queue_name: str = settings.RABBITMQ_STATUS_QUEUE,
        routing_key: str = ROUTING_KEY_STATUS_CHANGED,
    ) -> None:
        self.routing_key = routing_key
        self._url = url
        self._exchange_name = exchange_name
        self._queue_name = queue_name
        self._connection: RobustConnection | None = None
        self._channel: RobustChannel | None = None
        self._exchange: Exchange | None = None

    async def connect(self) -> AbstractRobustChannel:
        """Устанавливает надёжное подключение и объявляет exchange/очередь."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._url, timeout=5)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            queue = await self._channel.declare_queue(self._queue_name, durable=True)
            await queue.bind(self._exchange, routing_key=self.routing_key)
        return self._channel

    @property
    def exchange(self) -> Exchange:
        """Возвращает объявленный exchange."""
        if self._exchange is None:
            err_msg = "Не установлено подключение к RabbitMQ"
            raise RuntimeError(err_msg)
        return self._exchange

    async def check_connection(self) -> None:
        """Проверка доступности RabbitMQ."""
        connection = await aio_pika.connect_robust(self._url, timeout=5)
        await connection.close()

    async def close(self) -> None:
        """Закрывает соединение."""
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._exchange = None


rabbitmq_connection = RabbitMQConnection()
