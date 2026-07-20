from uuid import UUID, uuid4
import json
from litestar.exceptions import NotFoundException

from ..model import JournalEntry

# TODO: Make a logger
json_db_type = dict[UUID, JournalEntry]


class JsonDb:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: json_db_type = self.read_db_with_default(db_path)

    @staticmethod
    def read_db_with_default(db_path: str)->json_db_type:
        try: 
            with open(db_path, "r") as file:
                raw_db = json.load(file)
            return {UUID(id):JournalEntry(**entry) for id, entry in raw_db.items()}
        # TODO: don't overwrite on decoder error as that will destroy any existing data
        except (FileNotFoundError, json.JSONDecodeError):
            return dict()
        
    
    async def insert(self, entry: JournalEntry) -> JournalEntry:
        self.db[uuid4()] = entry
        await self.write_file()
        return entry
        
    async def list(self, **kwargs) -> list[JournalEntry]:
        return list(self.db.values())
        
    async def get(self, entry_id: UUID) -> JournalEntry:
        if entry_id not in self.db:
            raise NotFoundException(f"Journal entry {entry_id} not found")
        return self.db[entry_id]
        
    async def update(self, entry_id: UUID, data: JournalEntry) -> JournalEntry:
        if entry_id not in self.db:
            raise NotFoundException(f"Journal entry {entry_id} not found")
        
        self.db[entry_id] = data
        await self.write_file()
        return data
        
    async def delete(self, entry_id: UUID) -> None:
        if entry_id not in self.db:
            raise NotFoundException(f"Journal entry {entry_id} not found")

        del self.db[entry_id]
        await self.write_file()
        
    async def write_file(self):
        with open(self.db_path, "w") as file:
            json.dump(self.serialize(), file)
            
    def serialize(self) -> dict[str, JournalEntry]:
        return {str(uuid):entry.model_dump(mode='json') for uuid, entry in self.db.items()}

