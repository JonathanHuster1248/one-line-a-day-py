from uuid import UUID

from . import Database
from ..model import JournalUpdate, JournalCreate, JournalEntry
from ..settings import settings


# TODO: Actually point this to an SQL database using an ORM
class SqlDb(Database):
    db_path = settings.db_path
    db = None
    
    async def insert(self, data: JournalCreate) -> JournalEntry:
        pass 

    async def list(self, **kwargs) -> list[JournalEntry]:
        pass

    async def get(self, entry_id: UUID) -> JournalEntry:
        pass

    async def update(self, entry_id: UUID, data: JournalUpdate) -> JournalEntry:
        pass

    async def delete(self, entry_id: UUID) -> None:
        pass

    async def write_file(self):
        pass



