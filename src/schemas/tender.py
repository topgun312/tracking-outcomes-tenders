from pydantic import UUID4, BaseModel, Field

from src.schemas.response import BaseCreateResponse, BaseResponse
from src.schemas.tender_status_history import TenderStatusHistoryDB
from src.utils.constants import TenderStatus


class TenderID(BaseModel):
    id: UUID4


class CreateTenderRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    customer: str | None = Field(max_length=255, default=None)


class UpdateTenderStatusRequest(BaseModel):
    new_status: TenderStatus
    changed_by: str = Field(min_length=1, max_length=255)
    reason: str | None = None


class TenderDB(TenderID, CreateTenderRequest):
    status: TenderStatus


class TenderWithHistory(TenderDB):
    status_history: list[TenderStatusHistoryDB] = Field(default_factory=list)


class CreateTenderResponse(BaseCreateResponse):
    payload: TenderDB


class TenderResponse(BaseResponse):
    payload: TenderWithHistory
