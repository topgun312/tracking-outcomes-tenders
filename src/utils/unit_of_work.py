"""Модуль содержит базовые классы для поддержки транзакций."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Never

from src.database.db import async_session_maker
from src.repositories import TenderRepository, TenderStatusHistoryRepository


class AbstractUnitOfWork(ABC):
    is_open: bool
    tender: TenderRepository
    tender_status_history: TenderStatusHistoryRepository

    @abstractmethod
    def __init__(self) -> Never:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Never:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Never:
        raise NotImplementedError

    @abstractmethod
    async def flush(self) -> Never:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> Never:
        raise NotImplementedError


class UnitOfWork(AbstractUnitOfWork):
    """Класс, отвечающий за атомарность транзакций."""

    __slots__ = (
        "_session",
        "is_open",
        "tender",
        "tender_status_history",
    )

    def __init__(self) -> None:
        self.is_open = False

    async def __aenter__(self) -> None:
        self._session = async_session_maker()
        self.tender = TenderRepository(self._session)
        self.tender_status_history = TenderStatusHistoryRepository(self._session)
        self.is_open = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not exc_type:
            await self._session.commit()
        else:
            await self.rollback()
        await self._session.close()
        self.is_open = False

    async def flush(self) -> None:
        await self._session.flush()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def session_add(self, obj: Any) -> None:
        self._session.add(obj)

    async def session_refresh(self, obj: Any) -> None:
        await self._session.refresh(obj)

    def __getattr__(self, name: str) -> None:
        err_msg = f"У объекта '{self.__class__.__name__}' нет атрибута '{name}'"
        if name in self.__slots__ and not self.is_open:
            err_msg = f"Попытка обратиться к '{name}' при закрытом UnitOfWork"
        raise AttributeError(err_msg)
