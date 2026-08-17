__all__ = [
    "FakeBaseService",
    "FakeProducer",
    "FakeUnitOfWork",
    "db_mocks",
    "testing_cases",
]

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import TenderRepository, TenderStatusHistoryRepository
from src.utils.service import BaseService
from src.utils.unit_of_work import UnitOfWork
from tests.fixtures import db_mocks, testing_cases


class FakeProducer:
    """Test producer that records published messages without RabbitMQ."""

    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish_tender_status_change(self, **kwargs: object) -> None:
        self.published.append(kwargs)


class FakeUnitOfWork(UnitOfWork):
    """Test class for overriding the standard UnitOfWork."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    async def __aenter__(self) -> None:
        self.tender = TenderRepository(self._session)
        self.tender_status_history = TenderStatusHistoryRepository(self._session)
        self.is_open = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._session.flush()
        self.is_open = False


class FakeBaseService(BaseService):
    """Base service bound to the fake unit of work for tests."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.uow = FakeUnitOfWork(session)
