from copy import deepcopy
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.api.v1.services import TenderService
from src.models import TenderModel
from src.schemas.tender import CreateTenderRequest, TenderDB, UpdateTenderStatusRequest
from src.utils.constants import TenderStatus
from src.utils.custom_types import AsyncFunc
from tests.fixtures import FakeBaseService, FakeProducer, FakeUnitOfWork, testing_cases
from tests.utils import BaseTestCase

if TYPE_CHECKING:
    from collections.abc import Sequence


def _make_create_request(**kwargs: object) -> CreateTenderRequest:
    data: dict[str, object] = {
        "title": "Новый тендер",
        "description": "Описание",
        "customer": "ООО Тест",
    }
    data.update(kwargs)
    return CreateTenderRequest(**data)


class TestBaseService:
    class _BaseService(FakeBaseService):
        _repo = "tender"

    def __get_service(self, session: AsyncSession) -> FakeBaseService:
        return self._BaseService(session)

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_SERVICE_GET_BY_FILTER_ONE_OR_NONE_PARAMS
    )
    async def test_get_by_filter_one_or_none(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        with case.expected_error:
            tender: TenderModel | None = await service.get_by_filter_one_or_none(
                **case.data
            )
            assert (tender.to_schema().title if tender else None) == case.expected_data

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_SERVICE_GET_BY_FILTER_ALL_PARAMS
    )
    async def test_get_by_filter_all(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        with case.expected_error:
            tenders_in_db: Sequence[TenderModel] = await service.get_by_filter_all(
                **case.data
            )
            titles = sorted(t.to_schema().title for t in tenders_in_db)
            assert titles == sorted(case.expected_data)

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_SERVICE_UPDATE_ONE_BY_ID_PARAMS
    )
    async def test_update_one_by_id(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        data = deepcopy(case.data)
        with case.expected_error:
            updated: TenderModel | None = await service.update_one_by_id(
                data.pop("_id"), **data
            )
            assert updated is not None
            assert updated.to_schema().status == case.expected_data

    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_SERVICE_DELETE_BY_FILTER_PARAMS
    )
    async def test_delete_by_filter(
        self,
        case: BaseTestCase,
        transaction_session: AsyncSession,
        get_tenders: AsyncFunc,
    ) -> None:
        service = self.__get_service(transaction_session)
        with case.expected_error:
            await service.delete_by_filter(**case.data)
            tenders_in_db: Sequence[TenderModel] = await get_tenders()
            titles = sorted(t.to_schema().title for t in tenders_in_db)
            assert titles == sorted(case.expected_data)


class TestTenderService:
    def __get_service(self, session: AsyncSession) -> TenderService:
        return TenderService(uow=FakeUnitOfWork(session))

    async def test_create_tender(
        self,
        transaction_session: AsyncSession,
        get_tenders: AsyncFunc,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_producer = FakeProducer()
        monkeypatch.setattr(
            "src.api.v1.services.tender.producer", fake_producer, raising=False
        )
        service = self.__get_service(transaction_session)
        result: TenderDB = await service.create_tender(_make_create_request())
        assert result.status == TenderStatus.DRAFT
        assert result.title == "Новый тендер"

        tenders_in_db: Sequence[TenderModel] = await get_tenders()
        assert len(tenders_in_db) == 1
        assert len(fake_producer.published) == 1

    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    async def test_get_tender_with_history(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        result = await service.get_tender_with_history(
            "3d3e784f-646a-4ad4-979c-dca5dcea2a28"
        )
        assert str(result.id) == "3d3e784f-646a-4ad4-979c-dca5dcea2a28"
        assert result.status == TenderStatus.ACTIVE
        assert len(result.status_history) == 1

    async def test_get_tender_with_history_not_found(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.get_tender_with_history(uuid4())
        assert exc_info.value.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.usefixtures("setup_tenders")
    async def test_update_tender_status(
        self,
        transaction_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_producer = FakeProducer()
        monkeypatch.setattr(
            "src.api.v1.services.tender.producer", fake_producer, raising=False
        )
        service = self.__get_service(transaction_session)
        result = await service.update_tender_status(
            "d5621653-f72b-4124-98e6-79c5d9c2dc2b",
            UpdateTenderStatusRequest(
                new_status=TenderStatus.ACTIVE,
                changed_by="admin",
                reason="Публикация",
            ),
        )
        assert result.status == TenderStatus.ACTIVE
        assert len(fake_producer.published) == 1
        assert len(result.status_history) == 1
        assert result.status_history[0].new_status == TenderStatus.ACTIVE

    @pytest.mark.usefixtures("setup_tenders")
    async def test_update_tender_status_not_changed(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_tender_status(
                "3d3e784f-646a-4ad4-979c-dca5dcea2a28",
                UpdateTenderStatusRequest(
                    new_status=TenderStatus.ACTIVE,
                    changed_by="admin",
                    reason="Повтор",
                ),
            )
        assert exc_info.value.status_code == HTTP_400_BAD_REQUEST

    async def test_update_tender_status_not_found(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_tender_status(
                uuid4(),
                UpdateTenderStatusRequest(
                    new_status=TenderStatus.ACTIVE,
                    changed_by="admin",
                ),
            )
        assert exc_info.value.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    async def test_get_tender_status_history(
        self,
        transaction_session: AsyncSession,
    ) -> None:
        service = self.__get_service(transaction_session)
        history = await service.get_tender_status_history(
            UUID("3d3e784f-646a-4ad4-979c-dca5dcea2a28")
        )
        assert len(history) == 1
        assert history[0].new_status == TenderStatus.ACTIVE
