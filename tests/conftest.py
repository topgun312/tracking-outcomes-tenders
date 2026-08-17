from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Result, sql
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.config import settings
from src.main import app
from src.models import BaseModel
from src.utils.unit_of_work import UnitOfWork
from tests.fixtures import FakeUnitOfWork


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_db() -> None:
    """Создает тестовую базу данных на время выполнения тестов."""
    assert settings.MODE == "TEST", f"Expected MODE=TEST, got {settings.MODE}"

    nodb_engine = create_async_engine(
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/",
        echo=False,
        future=True,
    )
    db = AsyncSession(bind=nodb_engine)

    db_exists_query = sql.text(
        f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.DB_NAME}'"
    )
    db_exists: Result = await db.execute(db_exists_query)
    db_exists = db_exists.fetchone() is not None

    autocommit_engine = nodb_engine.execution_options(isolation_level="AUTOCOMMIT")
    connection = await autocommit_engine.connect()
    if not db_exists:
        await connection.execute(sql.text(f"CREATE DATABASE {settings.DB_NAME}"))

    yield

    await db.close()
    await connection.execute(
        sql.text(f"DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE)")
    )
    await connection.close()
    await nodb_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def db_engine(create_test_db: None) -> AsyncGenerator[AsyncEngine, None]:
    """Возвращает тестовый движок."""
    engine = create_async_engine(
        settings.DB_URL,
        echo=False,
        future=True,
        pool_size=50,
        max_overflow=100,
    ).execution_options(compiled_cache=None)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db(db_engine: AsyncEngine) -> None:
    """Создает таблицы в тестовой базе данных."""
    assert settings.MODE == "TEST"

    async with db_engine.begin() as db_conn:
        await db_conn.run_sync(BaseModel.metadata.drop_all)
        await db_conn.run_sync(BaseModel.metadata.create_all)


@pytest_asyncio.fixture
async def transaction_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Возвращает соединение с базой данных.

    Любые изменения, внесенные в базу данных, НЕ будут сохранены
    и будут действовать только в течение выполнения TestCase.
    """
    connection = await db_engine.connect()
    await connection.begin()
    session = AsyncSession(bind=connection)

    yield session

    await session.rollback()
    await connection.close()


@pytest_asyncio.fixture
def fake_uow(transaction_session: AsyncSession) -> FakeUnitOfWork:
    """Возвращает тестовый UnitOfWork для конкретного теста."""
    return FakeUnitOfWork(transaction_session)


@pytest_asyncio.fixture
async def async_client(fake_uow: FakeUnitOfWork) -> AsyncGenerator[AsyncClient, None]:
    """Возвращает асинхронный тестовый клиент."""
    app.dependency_overrides[UnitOfWork] = lambda: fake_uow
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(UnitOfWork, None)
