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

class JsonDb(Database):
    db_path = settings.db_path
    db = DB
    
    async def insert(self, data: JournalCreate) -> JournalEntry:
        entry = JournalEntry(**data.model_dump())
        self.db[entry.id] = entry
        await self.write_file()
        return entry

    async def list(self, **kwargs) -> list[JournalEntry]:
        list(self.db.values())

    async def get(self, entry_id: UUID) -> JournalEntry:
        if entry_id not in self.db:
            raise ValueError(f"Journal entry {entry_id} not found")
        return self.db[entry_id]

    async def update(self, entry_id: UUID, data: JournalUpdate) -> JournalEntry:
        if entry_id not in self.db:
            raise ValueError(f"Journal entry {entry_id} not found")

        existing = self.db[entry_id]
        updated = existing.copy(update=data.dict(exclude_unset=True))
        self.db[entry_id] = updated
        await self.write_file()
        return updated

    async def delete(self, entry_id: UUID) -> None:
        if entry_id not in self.db:
            raise ValueError(f"Journal entry {entry_id} not found")

        del self.db[entry_id]
        await self.write_file()

    async def write_file(self):
        with open(self.db_path, "w") as file:
            json.dump(self.db, file)


if __name__ == "__main__":
    from datetime import date
    db = JsonDb()
    new_entry = JournalCreate(date=date.today(), message="Another Great Day")
    db.insert(new_entry)
    print("Done entering data")

