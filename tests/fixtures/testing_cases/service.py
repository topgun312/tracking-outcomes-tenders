from tests.fixtures.db_mocks import TENDERS
from tests.utils import BaseTestCase

TEST_TENDER_SERVICE_GET_BY_FILTER_ONE_OR_NONE_PARAMS: list[BaseTestCase] = [
    BaseTestCase(
        data={"id": TENDERS[0]["id"]},
        expected_data="Поставка оборудования",
        description="Existing tender",
    ),
    BaseTestCase(
        data={"id": "00000000-0000-0000-0000-000000000000"},
        expected_data=None,
        description="Non-existent tender",
    ),
]

TEST_TENDER_SERVICE_GET_BY_FILTER_ALL_PARAMS: list[BaseTestCase] = [
    BaseTestCase(
        data={"status": "active"},
        expected_data=["Поставка оборудования"],
        description="Tenders with active status",
    ),
    BaseTestCase(
        data={"status": "no-such-status"},
        expected_data=[],
        description="No tenders with such status",
    ),
    BaseTestCase(
        data={},
        expected_data=["Поставка оборудования", "Ремонт офиса", "Закупка ПО"],
        description="All tenders",
    ),
]

TEST_TENDER_SERVICE_UPDATE_ONE_BY_ID_PARAMS: list[BaseTestCase] = [
    BaseTestCase(
        data={"_id": TENDERS[2]["id"], "status": "active"},
        expected_data="active",
        description="Update tender status",
    ),
]

TEST_TENDER_SERVICE_DELETE_BY_FILTER_PARAMS: list[BaseTestCase] = [
    BaseTestCase(
        data={"status": "draft"},
        expected_data=["Поставка оборудования", "Ремонт офиса"],
        description="Delete draft tenders",
    ),
]
