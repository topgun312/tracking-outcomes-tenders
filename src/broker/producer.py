import json
from datetime import datetime
from typing import Any
from uuid import UUID

from aio_pika import DeliveryMode, Message
from loguru import logger

from src.broker.connection import RabbitMQConnection, rabbitmq_connection


class TenderStatusProducer:
    """Публикует события изменения статуса тендеров в RabbitMQ."""

    def __init__(self, connection: RabbitMQConnection = rabbitmq_connection) -> None:
        self._connection = connection

    async def publish_tender_status_change(
        self,
        *,
        tender_id: UUID,
        old_status: str | None,
        new_status: str,
        changed_by: str,
        reason: str | None,
        changed_at: datetime,
    ) -> None:
        """Публикует событие изменения статуса тендера в RabbitMQ.

        Сбой брокера не должен прерывать выполнение запроса к API, поэтому ошибки логируются.
        """
        try:
            await self._connection.connect()
            payload: dict[str, Any] = {
                "tender_id": str(tender_id),
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": changed_by,
                "reason": reason,
                "changed_at": changed_at.isoformat(),
            }
            message = Message(
                body=json.dumps(payload, ensure_ascii=False).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
                timestamp=changed_at,
            )
            await self._connection.exchange.publish(
                message, routing_key=self._connection.routing_key
            )
            logger.info(
                "Изменение статуса тендера {} опубликовано: {} -> {}",
                tender_id,
                old_status,
                new_status,
            )
        except Exception as exc:
            logger.error(
                "Не удалось опубликовать изменение статуса тендера {} в RabbitMQ: {}",
                tender_id,
                exc,
            )


producer = TenderStatusProducer()
