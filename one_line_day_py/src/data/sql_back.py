from uuid import UUID

from ..model import JournalEntry, User, JournalTable, UserTable
from ..settings import settings

from sqlmodel import create_engine, SQLModel, Session, select

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


class UserSqlDb:
    def __init__(self, db_path: str):
        self.db_path = settings.db_path

    async def add_user(self, user: User) -> User:
        user_table = UserTable(user.name)
        with Session(engine) as session:
            session.add(user)
            session.commit()

    async def list_users(self, **kwargs) -> list[User]:
        pass

    async def get_user_by_id(self, user_id: UUID) -> User:
        with Session(engine) as session:
            statement = select(UserTable).where(UserTable.id == user_id)
            results = session.exec(statement)
            return results[0]

    async def get_user_id_by_name(self, user_id: UUID, user: User) -> User:
        pass

    async def update_user(self, user_id: UUID, updated_user: User) -> User:
        pass

    async def delete_user(self, user_id: UUID) -> None:
        pass


class JournalSqlDb:
    def __init__(self, db_path: str):
        self.db_path = settings.db_path

    async def add_journal(self, data: JournalEntry) -> JournalEntry:
        pass

    async def list_journals(self, **kwargs) -> list[JournalEntry]:
        pass

    async def get_journal(self, journal_id: UUID) -> JournalEntry:
        pass

    async def get_journal_author(self, journal_id: UUID) -> UUID:
        pass

    async def update_journal(
        self, journal_id: UUID, updated_journal: JournalEntry
    ) -> JournalEntry:
        pass

    async def delete_journal(self, journal_id: UUID) -> None:
        pass
