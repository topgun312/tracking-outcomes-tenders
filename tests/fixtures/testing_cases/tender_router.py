from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from tests.constants import BASE_ENDPOINT_URL
from tests.fixtures.db_mocks import TENDERS
from tests.utils import RequestTestCase

TEST_TENDER_ROUTE_CREATE_PARAMS: list[RequestTestCase] = [
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/",
        data={
            "title": "Поставка оборудования",
            "description": "Закупка серверов",
            "customer": "ООО Ромашка",
        },
        expected_status=HTTP_201_CREATED,
        expected_data={
            "title": "Поставка оборудования",
            "description": "Закупка серверов",
            "customer": "ООО Ромашка",
            "status": "draft",
        },
        description="Positive case",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/",
        data={"title": ""},
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data={},
        description="Empty title",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/",
        data={},
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data={},
        description="Missing title",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/",
        data={"title": "x" * 256},
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data={},
        description="Title too long",
    ),
]

TEST_TENDER_ROUTE_GET_PARAMS: list[RequestTestCase] = [
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/{TENDERS[0]['id']}",
        expected_status=HTTP_200_OK,
        expected_data={"title": "Поставка оборудования", "status": "active"},
        description="Positive case",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/1",
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data={},
        description="Not valid tender id",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        expected_status=HTTP_404_NOT_FOUND,
        expected_data={},
        description="Non-existent tender",
    ),
]

TEST_TENDER_ROUTE_UPDATE_STATUS_PARAMS: list[RequestTestCase] = [
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/{TENDERS[2]['id']}/status",
        data={
            "new_status": "active",
            "changed_by": "admin",
            "reason": "Публикация",
        },
        expected_status=HTTP_200_OK,
        expected_data={"status": "active"},
        description="Positive case",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/{TENDERS[0]['id']}/status",
        data={
            "new_status": "active",
            "changed_by": "admin",
            "reason": "Повтор",
        },
        expected_status=HTTP_400_BAD_REQUEST,
        expected_data={},
        description="Same status",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/{TENDERS[2]['id']}/status",
        data={
            "new_status": "invalid",
            "changed_by": "admin",
            "reason": "Ошибка",
        },
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data={},
        description="Not valid status",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/status",
        data={
            "new_status": "active",
            "changed_by": "admin",
            "reason": "Публикация",
        },
        expected_status=HTTP_404_NOT_FOUND,
        expected_data={},
        description="Non-existent tender",
    ),
]

TEST_TENDER_ROUTE_GET_STATUS_HISTORY_PARAMS: list[RequestTestCase] = [
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/{TENDERS[0]['id']}/status-history",
        expected_status=HTTP_200_OK,
        expected_data=[{"new_status": "active"}],
        description="Positive case",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/1/status-history",
        expected_status=HTTP_422_UNPROCESSABLE_CONTENT,
        expected_data=[],
        description="Not valid tender id",
    ),
    RequestTestCase(
        url=f"{BASE_ENDPOINT_URL}/tender/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/status-history",
        expected_status=HTTP_404_NOT_FOUND,
        expected_data=[],
        description="Non-existent tender",
    ),
]
