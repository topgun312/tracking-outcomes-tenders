from copy import deepcopy
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import TenderModel, TenderStatusHistoryModel
from src.repositories import TenderRepository, TenderStatusHistoryRepository
from src.utils.custom_types import AsyncFunc
from tests.fixtures import testing_cases
from tests.utils import BaseTestCase

if TYPE_CHECKING:
    from collections.abc import Sequence


class TestTenderRepository:
    def __get_repo(self, session: AsyncSession) -> TenderRepository:
        return TenderRepository(session)

    async def test_add_one_and_get_obj(
        self,
        transaction_session: AsyncSession,
        first_tender: dict,
        get_tenders: AsyncFunc,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        tender = await repo.add_one_and_get_obj(**first_tender)
        assert tender.id == first_tender["id"]
        await transaction_session.flush()

        tenders_in_db: Sequence[TenderModel] = await get_tenders()
        assert len(tenders_in_db) == 1
        assert tenders_in_db[0].id == first_tender["id"]

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case",
        testing_cases.TEST_SQLALCHEMY_REPOSITORY_GET_BY_FILTER_ONE_OR_NONE_PARAMS,
    )
    async def test_get_by_filter_one_or_none(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        with case.expected_error:
            tender: TenderModel | None = await repo.get_by_filter_one_or_none(
                **case.data
            )
            assert (tender.to_schema().title if tender else None) == case.expected_data

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_SQLALCHEMY_REPOSITORY_GET_BY_FILTER_ALL_PARAMS
    )
    async def test_get_by_filter_all(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        with case.expected_error:
            tenders_in_db: Sequence[TenderModel] = await repo.get_by_filter_all(
                **case.data
            )
            titles = sorted(t.to_schema().title for t in tenders_in_db)
            assert titles == sorted(case.expected_data)

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_SQLALCHEMY_REPOSITORY_UPDATE_ONE_BY_ID_PARAMS
    )
    async def test_update_one_by_id(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        data = deepcopy(case.data)
        with case.expected_error:
            updated: TenderModel | None = await repo.update_one_by_id(
                data.pop("_id"), **data
            )
            assert updated is not None
            assert updated.to_schema().status == case.expected_data

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_SQLALCHEMY_REPOSITORY_DELETE_BY_FILTER_PARAMS
    )
    async def test_delete_by_filter(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
        get_tenders: AsyncFunc,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        with case.expected_error:
            await repo.delete_by_filter(**case.data)
            await transaction_session.flush()
            tenders_in_db: Sequence[TenderModel] = await get_tenders()
            titles = sorted(t.to_schema().title for t in tenders_in_db)
            assert titles == sorted(case.expected_data)

    @pytest.mark.usefixtures("setup_tenders")
    async def test_delete_all(
        self,
        transaction_session: AsyncSession,
        get_tenders: AsyncFunc,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        await repo.delete_all()
        await transaction_session.flush()
        tenders_in_db: Sequence[TenderModel] = await get_tenders()
        assert tenders_in_db == []

    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    async def test_get_tender_with_history(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        tender = await repo.get_tender_with_history(
            "3d3e784f-646a-4ad4-979c-dca5dcea2a28"
        )
        assert tender is not None
        assert len(tender.status_history) == 1
        assert tender.status_history[0].new_status == "active"


class TestTenderStatusHistoryRepository:
    def __get_repo(self, session: AsyncSession) -> TenderStatusHistoryRepository:
        return TenderStatusHistoryRepository(session)

    @pytest.mark.usefixtures("setup_tenders")
    async def test_add_one_and_get_obj(
        self,
        transaction_session: AsyncSession,
        first_status_history_entry: dict,
        get_tender_status_history: AsyncFunc,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        entry = await repo.add_one_and_get_obj(**first_status_history_entry)
        assert entry.tender_id == first_status_history_entry["tender_id"]
        await transaction_session.flush()

        history_in_db: Sequence[TenderStatusHistoryModel] = (
            await get_tender_status_history()
        )
        assert len(history_in_db) == 1
        assert history_in_db[0].new_status == first_status_history_entry["new_status"]

    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    async def test_get_by_filter_one_or_none(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        entry = await repo.get_by_filter_one_or_none(
            id=UUID("e4f21ac0-8b40-4f2a-9c1e-5b0d4e3a2a01")
        )
        assert entry is not None
        assert entry.new_status == "active"

    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    async def test_get_by_filter_all(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        repo = self.__get_repo(transaction_session)
        entries = await repo.get_by_filter_all(
            tender_id="3d3e784f-646a-4ad4-979c-dca5dcea2a28"
        )
        assert len(entries) == 1
