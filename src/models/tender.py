from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import BaseModel
from src.schemas.tender import TenderDB
from src.utils.custom_types import created_at, updated_at, uuid_pk

if TYPE_CHECKING:
    from src.models.tender_status_history import TenderStatusHistoryModel


class TenderModel(BaseModel):
    __tablename__ = "tender"

    id: Mapped[uuid_pk]
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    customer: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    status_history: Mapped[list["TenderStatusHistoryModel"]] = relationship(
        back_populates="tender",
        cascade="all, delete-orphan",
        order_by="TenderStatusHistoryModel.created_at",
    )

    def to_schema(self) -> TenderDB:
        return TenderDB(**self.__dict__)
