from collections.abc import Sequence
from copy import deepcopy

import pytest
import pytest_asyncio
from sqlalchemy import Result, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import TenderModel, TenderStatusHistoryModel
from src.utils.custom_types import AsyncFunc
from tests import fixtures
from tests.utils import bulk_save_models


@pytest_asyncio.fixture
async def setup_tenders(
    transaction_session: AsyncSession, tenders: tuple[dict]
) -> None:
    """Создает тендеры, которые будут существовать только в рамках сеанса."""
    await bulk_save_models(transaction_session, TenderModel, tenders)


@pytest_asyncio.fixture
async def setup_tender_status_history(
    transaction_session: AsyncSession, tender_status_history: tuple[dict]
) -> None:
    """Создает записи истории статусов, которые будут существовать только в рамках сеанса."""
    await bulk_save_models(
        transaction_session, TenderStatusHistoryModel, tender_status_history
    )


@pytest_asyncio.fixture
def get_tenders(transaction_session: AsyncSession) -> AsyncFunc:
    """Возвращает тендеры, существующие в рамках сеанса."""

    async def _get_tenders() -> Sequence[TenderModel]:
        res: Result = await transaction_session.execute(select(TenderModel))
        return res.scalars().all()

    return _get_tenders


@pytest_asyncio.fixture
def get_tender_status_history(transaction_session: AsyncSession) -> AsyncFunc:
    """Возвращает записи истории состояний, существующие в рамках сеанса."""

    async def _get_tender_status_history() -> Sequence[TenderStatusHistoryModel]:
        res: Result = await transaction_session.execute(
            select(TenderStatusHistoryModel)
        )
        return res.scalars().all()

    return _get_tender_status_history


@pytest.fixture
def tenders() -> tuple[dict]:
    return deepcopy(fixtures.db_mocks.TENDERS)


@pytest.fixture
def tender_status_history() -> tuple[dict]:
    return deepcopy(fixtures.db_mocks.TENDER_STATUS_HISTORY)


@pytest.fixture
def first_tender() -> dict:
    return deepcopy(fixtures.db_mocks.TENDERS[0])


@pytest.fixture
def first_status_history_entry() -> dict:
    return deepcopy(fixtures.db_mocks.TENDER_STATUS_HISTORY[0])
