from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import BaseModel
from src.schemas.tender_status_history import TenderStatusHistoryDB
from src.utils.custom_types import created_at, uuid_pk

if TYPE_CHECKING:
    from src.models.tender import TenderModel


class TenderStatusHistoryModel(BaseModel):
    __tablename__ = "tender_status_history"

    id: Mapped[uuid_pk]
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tender.id", ondelete="CASCADE"),
        index=True,
    )
    old_status: Mapped[str | None] = mapped_column(String(20), default=None)
    new_status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[created_at]

    tender: Mapped["TenderModel"] = relationship(back_populates="status_history")

    def to_schema(self) -> TenderStatusHistoryDB:
        return TenderStatusHistoryDB(**self.__dict__)
