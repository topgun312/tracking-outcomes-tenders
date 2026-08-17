from datetime import datetime

from pydantic import UUID4, BaseModel

from src.schemas.response import BaseResponse
from src.utils.constants import TenderStatus


class TenderStatusHistoryID(BaseModel):
    id: UUID4


class TenderStatusHistoryDB(TenderStatusHistoryID):
    tender_id: UUID4
    old_status: TenderStatus | None
    new_status: TenderStatus
    changed_by: str
    reason: str | None
    created_at: datetime


class TenderStatusHistoryResponse(BaseResponse):
    payload: list[TenderStatusHistoryDB]
