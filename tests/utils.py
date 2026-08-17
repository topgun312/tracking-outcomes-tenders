from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager, nullcontext
from typing import Any, TypeVar

from httpx import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from starlette.status import HTTP_200_OK

Check = Callable[[dict[str, Any]], bool]
T = TypeVar("T")


class BaseConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class TestDescription(BaseConfig):
    description: str = ""


class TestExpectation(BaseConfig):
    expected_error: AbstractContextManager = nullcontext()
    expected_status: int = HTTP_200_OK
    expected_data: Any = None
    checks: Iterable[Check] | None = None


class BaseTestCase(TestDescription, TestExpectation):
    data: dict | None = None


class RequestTestCase(BaseTestCase):
    url: str = ""
    headers: dict | None = None


async def bulk_save_models(
    session: AsyncSession,
    model: type[DeclarativeBase],
    data: Iterable[dict[str, Any]],
    *,
    commit: bool = False,
) -> None:
    """Массово сохраняет объекты модели в базу данных."""
    for values in data:
        await session.execute(insert(model).values(**values))

    if commit:
        await session.commit()
    else:
        await session.flush()


def _to_schema_dict(item: Any, schema: type[BaseModel]) -> BaseModel:
    """Преобразует модель или словарь в указанную схему Pydantic."""
    obj = getattr(item, "to_schema", None)
    if obj is not None:
        item = obj()
    if isinstance(item, BaseModel):
        return schema(**item.model_dump())
    if isinstance(item, dict):
        return schema(**item)
    return schema(**item.__dict__)


def compare_dicts_and_db_models(
    result: Sequence[Any] | None,
    expected_result: Sequence[dict] | None,
    schema: type[BaseModel],
) -> bool:
    """Сравнивает модели из базы данных с ожидаемыми словарями."""
    if result is None or expected_result is None:
        return result == expected_result

    result_to_schema = [_to_schema_dict(item, schema) for item in result]
    expected_result_to_schema = [
        _to_schema_dict(item, schema) for item in expected_result
    ]

    equality_len = len(result_to_schema) == len(expected_result_to_schema)
    equality_obj = all(obj in expected_result_to_schema for obj in result_to_schema)
    return all((equality_len, equality_obj))


def models_to_dicts(
    models: Sequence[Any],
    exclude: Sequence[str] | None = None,
) -> list[dict]:
    """Преобразует последовательность моделей в словари,
    при необходимости исключая определенные ключи."""
    result = []
    for model in models:
        to_schema = getattr(model, "to_schema", None)
        obj = to_schema() if to_schema is not None else model
        data = obj.model_dump()
        for key in exclude or ():
            data.pop(key, None)
        result.append(data)
    return result


def prepare_payload(response: Response, exclude: Sequence[str] | None = None) -> dict:
    """Извлекает полезную нагрузку из ответа."""
    payload = response.json().get("payload")
    if payload is None:
        return {}

    if exclude is None:
        return payload

    for key in exclude:
        payload.pop(key, None)

    return payload
