from uuid import UUID
import json
from litestar.exceptions import NotFoundException

from . import Database
from ..model import JournalEntry
from ..settings import settings, DbType

# TODO: Make a logger
json_db_type = dict[str, JournalEntry]
if settings.db_type == DbType.JSON:
    try: 
        with open(settings.db_path, "r") as file:
            raw_db = json.load(file)
        DB: json_db_type = {id:JournalEntry(**entry) for id, entry in raw_db.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        DB: json_db_type = dict()
else: 
    DB: json_db_type = dict()


class JsonDb(Database):
    db_path = settings.db_path
    db = DB
    
    @classmethod
    async def insert(cls, entry: JournalEntry) -> JournalEntry:
        cls.db[str(entry.id)] = entry
        await cls.write_file()
        return entry
        
    @classmethod
    async def list(cls, **kwargs) -> list[JournalEntry]:
        return list(cls.db.values())
        
    @classmethod
    async def get(cls, entry_id: UUID) -> JournalEntry:
        if entry_id not in cls.db:
            raise NotFoundException(f"Journal entry {entry_id} not found")
        return cls.db[entry_id]
        
    @classmethod
    async def update(cls, entry_id: UUID, data: JournalEntry) -> JournalEntry:
        entry_id = str(entry_id)
        if entry_id not in cls.db:
            raise NotFoundException(f"Journal entry {entry_id} not found")

        existing = cls.db[entry_id]
        to_update = {key: value for key, value in data.model_dump().items() if value}
        updated = existing.model_copy(update=to_update)
        cls.db[entry_id] = updated
        await cls.write_file()
        return updated
        
    @classmethod
    async def delete(cls, entry_id: UUID) -> None:
        id_str = str(entry_id)
        if id_str not in cls.db:
            raise NotFoundException(f"Journal entry {id_str} not found")

        del cls.db[id_str]
        await cls.write_file()
        
    @classmethod
    async def write_file(cls):
        with open(cls.db_path, "w") as file:
            json.dump(cls.serialize_db(cls.db), file)
            
    @staticmethod
    def serialize_db(db: dict[UUID, JournalEntry]) -> dict[str, JournalEntry]:
        return {uuid:entry.serialized for uuid, entry in db.items()}

