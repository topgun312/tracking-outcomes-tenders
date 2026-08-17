from src.models import TenderStatusHistoryModel
from src.utils.repository import SqlAlchemyRepository


class TenderStatusHistoryRepository(SqlAlchemyRepository[TenderStatusHistoryModel]):
    _model = TenderStatusHistoryModel
