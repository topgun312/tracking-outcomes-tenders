from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from src.api.v1.services import TenderService
from src.schemas.tender import (
    CreateTenderRequest,
    CreateTenderResponse,
    TenderDB,
    TenderResponse,
    TenderWithHistory,
    UpdateTenderStatusRequest,
)
from src.schemas.tender_status_history import (
    TenderStatusHistoryDB,
    TenderStatusHistoryResponse,
)

router = APIRouter(prefix="/tender")


@router.post(
    path="/",
    status_code=HTTP_201_CREATED,
)
async def create_tender(
    tender: CreateTenderRequest,
    service: TenderService = Depends(),
) -> CreateTenderResponse:
    """Создание тендера."""
    created_tender: TenderDB = await service.create_tender(tender)
    return CreateTenderResponse(payload=created_tender)


@router.get(
    path="/{tender_id}/status-history",
    status_code=HTTP_200_OK,
)
async def get_tender_status_history(
    tender_id: UUID4,
    service: TenderService = Depends(),
) -> TenderStatusHistoryResponse:
    """Получение истории статусов тендера по ID."""
    history: list[TenderStatusHistoryDB] = await service.get_tender_status_history(
        tender_id
    )
    return TenderStatusHistoryResponse(payload=history)


@router.patch(
    path="/{tender_id}/status",
    status_code=HTTP_200_OK,
)
async def update_tender_status(
    tender_id: UUID4,
    payload: UpdateTenderStatusRequest,
    service: TenderService = Depends(),
) -> TenderResponse:
    """Обновление статуса тендера."""
    updated_tender: TenderWithHistory = await service.update_tender_status(
        tender_id, payload
    )
    return TenderResponse(payload=updated_tender)


@router.get(
    path="/{tender_id}",
    status_code=HTTP_200_OK,
)
async def get_tender(
    tender_id: UUID4,
    service: TenderService = Depends(),
) -> TenderResponse:
    """Получение тендера по ID."""
    tender: TenderWithHistory = await service.get_tender_with_history(tender_id)
    return TenderResponse(payload=tender)
