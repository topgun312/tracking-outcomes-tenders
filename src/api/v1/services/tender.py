from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException
from pydantic import UUID4
from starlette.status import HTTP_400_BAD_REQUEST

from src.broker.producer import producer
from src.schemas.tender import (
    CreateTenderRequest,
    TenderDB,
    TenderWithHistory,
    UpdateTenderStatusRequest,
)
from src.schemas.tender_status_history import TenderStatusHistoryDB
from src.utils.constants import (
    TENDER_NOT_FOUND_MSG,
    TENDER_STATUS_NOT_CHANGED_MSG,
    TenderStatus,
)
from src.utils.service import BaseService, transaction_mode

if TYPE_CHECKING:
    from src.models import TenderModel
from src.models import TenderStatusHistoryModel


class TenderService(BaseService):
    _repo: str = "tender"

    @transaction_mode(auto_flush=True)
    async def create_tender(self, tender: CreateTenderRequest) -> TenderDB:
        """Создание тендера с начальным статусом."""
        created_tender: TenderModel = await self.uow.tender.add_one_and_get_obj(
            **tender.model_dump()
        )
        await self.uow.session_add(
            TenderStatusHistoryModel(
                tender_id=created_tender.id,
                old_status=None,
                new_status=TenderStatus.DRAFT.value,
                changed_by="system",
                reason="Тендер создан",
            )
        )
        await producer.publish_tender_status_change(
            tender_id=created_tender.id,
            old_status=None,
            new_status=TenderStatus.DRAFT.value,
            changed_by="system",
            reason="Тендер создан",
            changed_at=created_tender.created_at,
        )
        return created_tender.to_schema()

    @transaction_mode
    async def get_tender_with_history(self, tender_id: UUID4) -> TenderWithHistory:
        """Получение тендера по ID со всей историей статусов."""
        tender: TenderModel | None = await self.uow.tender.get_tender_with_history(
            tender_id
        )
        self.check_existence(obj=tender, details=TENDER_NOT_FOUND_MSG)
        return TenderWithHistory(
            id=tender.id,
            title=tender.title,
            description=tender.description,
            customer=tender.customer,
            status=tender.status,
            status_history=[entry.to_schema() for entry in tender.status_history],
        )

    @transaction_mode(auto_flush=True)
    async def update_tender_status(
        self,
        tender_id: UUID4,
        payload: UpdateTenderStatusRequest,
    ) -> TenderWithHistory:
        """Обновление статуса тендера и фиксация изменения в таблице истории."""
        tender: TenderModel | None = await self.uow.tender.get_by_filter_one_or_none(
            id=tender_id
        )
        self.check_existence(obj=tender, details=TENDER_NOT_FOUND_MSG)

        old_status = TenderStatus(tender.status)
        new_status = payload.new_status
        if old_status == new_status:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=TENDER_STATUS_NOT_CHANGED_MSG
            )

        await self.uow.tender.update_one_by_id(
            obj_id=tender_id, status=new_status.value
        )
        history: TenderStatusHistoryModel = TenderStatusHistoryModel(
            tender_id=tender_id,
            old_status=old_status.value,
            new_status=new_status.value,
            changed_by=payload.changed_by,
            reason=payload.reason,
        )
        await self.uow.session_add(history)
        await self.uow.flush()

        await producer.publish_tender_status_change(
            tender_id=tender_id,
            old_status=old_status.value,
            new_status=new_status.value,
            changed_by=payload.changed_by,
            reason=payload.reason,
            changed_at=datetime.now(timezone.utc),
        )

        tender_with_history = await self.get_tender_with_history(tender_id)
        tender_with_history.status_history.append(history.to_schema())
        return tender_with_history

    @transaction_mode
    async def get_tender_status_history(
        self, tender_id: UUID4
    ) -> list[TenderStatusHistoryDB]:
        """Получение истории статусов тендера по ID."""
        tender: TenderModel | None = await self.uow.tender.get_tender_with_history(
            tender_id
        )
        self.check_existence(obj=tender, details=TENDER_NOT_FOUND_MSG)
        return [entry.to_schema() for entry in tender.status_history]
