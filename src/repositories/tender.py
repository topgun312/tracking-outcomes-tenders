from pydantic import UUID4
from sqlalchemy import Result, select
from sqlalchemy.orm import selectinload

from src.models import TenderModel
from src.utils.repository import SqlAlchemyRepository


class TenderRepository(SqlAlchemyRepository[TenderModel]):
    _model = TenderModel

    async def get_tender_with_history(self, tender_id: UUID4) -> TenderModel | None:
        """Поиск тендера по ID со всей историей статусов."""
        query = (
            select(self._model)
            .where(self._model.id == tender_id)
            .options(selectinload(self._model.status_history))
        )
        res: Result = await self._session.execute(query)
        return res.unique().scalar_one_or_none()
