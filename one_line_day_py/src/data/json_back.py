from uuid import UUID
import json

from . import Database
from ..model import JournalUpdate, JournalCreate, JournalEntry
from ..settings import settings, DbType

# TODO: Make a logger
json_db_type = dict[UUID, JournalEntry]
if settings.db_type == DbType.JSON:
    try: 
        with open(settings.db_path, "r") as file:
            raw_db = json.load(file)
        DB: json_db_type = {id:JournalEntry(**entry) for id, entry in raw_db.items()}
    except FileNotFoundError:
        DB: json_db_type = dict()
else: 
    DB: json_db_type = dict()

# from datetime import date
# test_journal = JournalEntry(date=date.today(), message="Wow today was so cool")
# DB: dict[UUID, JournalEntry] = {test_journal.id:test_journal}  


class JsonDb(Database):
    db_path = settings.db_path
    db = DB
    
    @classmethod
    async def insert(cls, data: JournalCreate) -> JournalEntry:
        entry = JournalEntry(**data.model_dump())
        cls.db[entry.id] = entry
        await cls.write_file()
        return entry
        
    @classmethod
    async def list(cls, **kwargs) -> list[JournalEntry]:
        return list(cls.db.values())
        
    @classmethod
    async def get(cls, entry_id: UUID) -> JournalEntry:
        if entry_id not in cls.db:
            raise ValueError(f"Journal entry {entry_id} not found")
        return cls.db[entry_id]
        
    @classmethod
    async def update(cls, entry_id: UUID, data: JournalUpdate) -> JournalEntry:
        if entry_id not in cls.db:
            raise ValueError(f"Journal entry {entry_id} not found")

        existing = cls.db[entry_id]
        updated = existing.copy(update=data.dict(exclude_unset=True))
        cls.db[entry_id] = updated
        await cls.write_file()
        return updated
        
    @classmethod
    async def delete(cls, entry_id: UUID) -> None:
        if entry_id not in cls.db:
            raise ValueError(f"Journal entry {entry_id} not found")

        del cls.db[entry_id]
        await cls.write_file()
        
    @classmethod
    async def write_file(cls):
        with open(cls.db_path, "w") as file:
            json.dump(self.db, file)


if __name__ == "__main__":
    from datetime import date
    from asyncio import run
    # db = JsonDb()
    # new_entry = JournalCreate(date=date.today(), message="Another Great Day")
    # db.insert(new_entry)
    entries = run(JsonDb.list())
    print(f"{entries}")

