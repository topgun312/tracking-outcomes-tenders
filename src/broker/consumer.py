import asyncio

from loguru import logger

from src.broker.connection import RabbitMQConnection, rabbitmq_connection
from src.config import settings


class TenderStatusConsumer:
    """Потребляет события изменения статуса тендеров и логирует их."""

    def __init__(self, connection: RabbitMQConnection = rabbitmq_connection) -> None:
        self._connection = connection

    async def consume(self) -> None:
        """Потребляет события изменения статуса тендеров и логирует их."""
        while True:
            try:
                channel = await self._connection.connect()
                break
            except Exception as exc:
                logger.warning(
                    "Не удалось подключиться к RabbitMQ ({}), повтор через 5 с...", exc
                )
                await asyncio.sleep(5)
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(
            settings.RABBITMQ_STATUS_QUEUE, durable=True
        )
        logger.info(
            "Консюмер RabbitMQ запущен, ожидаются обновления статуса тендеров..."
        )
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    logger.info(
                        "Получено изменение статуса тендера: {}", message.body.decode()
                    )

    async def run(self) -> None:
        """Запускает консюмер до его остановки."""
        await self.consume()


consumer = TenderStatusConsumer()


if __name__ == "__main__":
    asyncio.run(consumer.run())
