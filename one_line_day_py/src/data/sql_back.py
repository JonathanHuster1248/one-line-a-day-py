from uuid import UUID

from ..model import JournalEntry
from ..settings import settings

from sqlmodel import create_engine, Session, SQLModel
from sqlmodel import SQLModel, Field

DATABASE_URL = "sqlite:///journal.db"

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)


class SqlDb:

    def __init__(self, db_path: str):
        self.db_path = settings.db_path
    
    async def insert(self, data: JournalEntry) -> JournalEntry:
        pass 

    async def list(self, **kwargs) -> list[JournalEntry]:
        pass

    async def get(self, entry_id: UUID) -> JournalEntry:
        pass

    async def update(self, entry_id: UUID, data: JournalEntry) -> JournalEntry:
        pass

    async def delete(self, entry_id: UUID) -> None:
        pass

    async def write_file(self):
        pass



