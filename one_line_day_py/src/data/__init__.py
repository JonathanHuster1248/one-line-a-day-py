from typing import Protocol
from uuid import UUID

from ..model import JournalEntry

class Database(Protocol):

    async def insert(self, data: JournalEntry) -> JournalEntry:
        ...

    async def list(self, **kwargs) -> list[JournalEntry]:
        ...

    async def get(self, entry_id: UUID) -> JournalEntry:
        ...

    async def update(self, entry_id: UUID, data: JournalEntry) -> JournalEntry:
        ...

    async def delete(self, entry_id: UUID) -> None:
        ...


