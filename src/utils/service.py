"""Модуль содержит базовый сервис."""

import functools
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Never, TypeVar, overload
from uuid import UUID

from fastapi import Depends, HTTPException
from starlette.status import HTTP_404_NOT_FOUND

from src.utils.repository import AbstractRepository
from src.utils.unit_of_work import AbstractUnitOfWork, UnitOfWork

T = TypeVar("T", bound=Callable[..., Awaitable[Any]])


@overload
def transaction_mode(_func: T) -> T: ...
@overload
def transaction_mode(*, auto_flush: bool) -> Callable[[T], T]: ...


def transaction_mode(
    _func: T | None = None, *, auto_flush: bool = False
) -> T | Callable[[T], T]:
    """Оборачивает функцию в транзакционный режим.
    Проверяет, открыт ли контекстный менеджер UnitOfWork.
    Если нет — открывает контекстный менеджер и запускает транзакцию.
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(self: AbstractService, *args: Any, **kwargs: Any) -> Any:
            if self.uow.is_open:
                res = await func(self, *args, **kwargs)
                if auto_flush:
                    await self.uow.flush()
                return res
            async with self.uow:
                return await func(self, *args, **kwargs)

        return wrapper

    if _func is None:  # Использование с параметрами: @transaction_mode(auto_flush=True)
        return decorator
    return decorator(_func)  # Использование без параметров: @transaction_mode


class AbstractService(ABC):
    """Абстрактный класс, реализующий CRUD-операции на уровне сервиса."""

    uow: AbstractUnitOfWork

    @abstractmethod
    async def add_one(self, *args: Any, **kwargs: Any) -> Never:
        """Добавление одной записи."""
        raise NotImplementedError

    @abstractmethod
    async def add_one_and_get_id(self, *args: Any, **kwargs: Any) -> Never:
        """Добавление одной записи и получение её ID."""
        raise NotImplementedError

    @abstractmethod
    async def add_one_and_get_obj(self, *args: Any, **kwargs: Any) -> Never:
        """Добавление одной записи и получение этой записи."""
        raise NotImplementedError

    @abstractmethod
    async def bulk_add(self, *args: Any, **kwargs: Any) -> Never:
        """Массовое добавление записей."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_filter_one_or_none(self, *args: Any, **kwargs: Any) -> Never:
        """Получение одной записи по фильтру, если она существует."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_filter_all(self, *args: Any, **kwargs: Any) -> Never:
        """Получение всех записей по заданному фильтру."""
        raise NotImplementedError

    @abstractmethod
    async def update_one_by_id(self, *args: Any, **kwargs: Any) -> Never:
        """Обновление записи по её ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_by_filter(self, *args: Any, **kwargs: Any) -> Never:
        """Массовое удаление записей по фильтру."""
        raise NotImplementedError

    @abstractmethod
    async def delete_by_ids(self, *args: Any, **kwargs: Any) -> Never:
        """Массовое удаление записей по переданным ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_all(self, *args: Any, **kwargs: Any) -> Never:
        """Массовое удаление всех записей."""
        raise NotImplementedError


class BaseService(AbstractService):
    """Базовый сервис для выполнения стандартных CRUD-операций с базовым репозиторием."""

    _repo: str | None = (
        None  # должен быть строкой — атрибутом класса AbstractUnitOfWork
    )

    def __init__(self, uow: UnitOfWork = Depends()) -> None:
        """Создаёт экземпляр базового сервиса.

        Если дочерний класс зависит от другого сервиса и хочет использовать его
        функциональность, необходимо явно указать зависимость через `Depends`, например:
            def __init__(self, uow: UnitOfWork = Depends(), other_service: OtherService = Depends())
        """
        self.uow: UnitOfWork = uow
        if not hasattr(self, "_repo") or self._repo is None:
            err_msg = f"Атрибут '_repo' обязателен для класса {self.__class__.__name__}"
            raise AttributeError(err_msg)

    @transaction_mode
    async def add_one(self, **kwargs: Any) -> None:
        await self._get_related_repo().add_one(**kwargs)

    @transaction_mode
    async def add_one_and_get_id(self, **kwargs: Any) -> int | str | UUID:
        return await self._get_related_repo().add_one_and_get_id(**kwargs)

    @transaction_mode
    async def add_one_and_get_obj(self, **kwargs: Any) -> Any:
        return await self._get_related_repo().add_one_and_get_obj(**kwargs)

    @transaction_mode
    async def bulk_add(self, values: Sequence[dict[str, Any]]) -> None:
        await self._get_related_repo().bulk_add(values=values)

    @transaction_mode
    async def get_by_filter_one_or_none(self, **kwargs: Any) -> Any:
        return await self._get_related_repo().get_by_filter_one_or_none(**kwargs)

    @transaction_mode
    async def get_by_filter_all(self, **kwargs: Any) -> Sequence[Any]:
        return await self._get_related_repo().get_by_filter_all(**kwargs)

    @transaction_mode
    async def update_one_by_id(self, obj_id: int | str | UUID, **kwargs: Any) -> Any:
        return await self._get_related_repo().update_one_by_id(obj_id=obj_id, **kwargs)

    @transaction_mode
    async def delete_by_filter(self, **kwargs: Any) -> None:
        await self._get_related_repo().delete_by_filter(**kwargs)

    @transaction_mode
    async def delete_by_ids(self, *args: int | str | UUID) -> None:
        await self._get_related_repo().delete_by_ids(*args)

    @transaction_mode
    async def delete_all(self) -> None:
        await self._get_related_repo().delete_all()

    @staticmethod
    def check_existence(obj: Any, details: str) -> None:
        """Проверка существования объекта."""
        if not obj:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=details)

    def _get_related_repo(self) -> AbstractRepository:
        """Возвращает репозиторий, связанный с сервисом."""
        return getattr(self.uow, self._repo)
