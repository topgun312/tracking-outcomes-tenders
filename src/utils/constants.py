"""Модуль содержит константы приложения."""

from enum import Enum


class TenderStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"


TENDER_STATUS_LABELS: dict[TenderStatus, str] = {
    TenderStatus.DRAFT: "Черновик",
    TenderStatus.ACTIVE: "Активен",
    TenderStatus.WON: "Выигран",
    TenderStatus.LOST: "Проигран",
}

TENDER_NOT_FOUND_MSG = "Тендер не найден"
TENDER_STATUS_NOT_CHANGED_MSG = "Статус тендера не изменился"
