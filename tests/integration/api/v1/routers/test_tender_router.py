import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.fixtures import FakeProducer, testing_cases
from tests.utils import RequestTestCase, prepare_payload


@pytest_asyncio.fixture
async def async_client_with_producer(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> tuple[AsyncClient, FakeProducer]:
    """Тестовый клиент с фиктивным производителем для тестов, проверяющих изменение статуса."""
    fake_producer = FakeProducer()
    monkeypatch.setattr(
        "src.api.v1.services.tender.producer", fake_producer, raising=False
    )
    return async_client, fake_producer


class TestTenderRouter:
    @staticmethod
    @pytest.mark.parametrize("case", testing_cases.TEST_TENDER_ROUTE_CREATE_PARAMS)
    async def test_create(case: RequestTestCase, async_client: AsyncClient) -> None:
        with case.expected_error:
            response = await async_client.post(
                case.url, json=case.data, headers=case.headers
            )
            assert response.status_code == case.expected_status
            assert (
                prepare_payload(response, ["id", "created_at", "updated_at"])
                == case.expected_data
            )

    @staticmethod
    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize("case", testing_cases.TEST_TENDER_ROUTE_GET_PARAMS)
    async def test_get(case: RequestTestCase, async_client: AsyncClient) -> None:
        with case.expected_error:
            response = await async_client.get(case.url, headers=case.headers)
            assert response.status_code == case.expected_status
            payload = prepare_payload(response)
            if case.expected_data:
                assert payload["title"] == case.expected_data["title"]
                assert payload["status"] == case.expected_data["status"]

    @staticmethod
    @pytest.mark.usefixtures("setup_tenders", "setup_tender_status_history")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_ROUTE_GET_STATUS_HISTORY_PARAMS
    )
    async def test_get_status_history(
        case: RequestTestCase, async_client: AsyncClient
    ) -> None:
        with case.expected_error:
            response = await async_client.get(case.url, headers=case.headers)
            assert response.status_code == case.expected_status
            payload = prepare_payload(response)
            if case.expected_data:
                assert payload[0]["new_status"] == case.expected_data[0]["new_status"]

    @staticmethod
    @pytest.mark.usefixtures("setup_tenders")
    @pytest.mark.parametrize(
        "case", testing_cases.TEST_TENDER_ROUTE_UPDATE_STATUS_PARAMS
    )
    async def test_update_status(
        case: RequestTestCase,
        async_client_with_producer: tuple[AsyncClient, FakeProducer],
    ) -> None:
        async_client, fake_producer = async_client_with_producer
        with case.expected_error:
            response = await async_client.patch(
                case.url, json=case.data, headers=case.headers
            )
            assert response.status_code == case.expected_status
            if case.expected_data:
                assert (
                    prepare_payload(response)["status"] == case.expected_data["status"]
                )
                assert fake_producer.published
