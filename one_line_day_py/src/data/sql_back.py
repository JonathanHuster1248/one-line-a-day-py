from uuid import UUID

from ..model import JournalEntry, User
from ..settings import settings

from sqlmodel import create_engine, SQLModel, Session, select


def init_db(db_path: str):
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


class UserSqlDb:
    def __init__(self, db_path: str):
        self.engine = init_db(db_path)

    async def add_user(self, user: User) -> User:
        user_table = User(name=user.name)
        with Session(self.engine) as session:
            session.add(user_table)
            session.commit()
        return user

    async def list_users(self, **kwargs) -> list[User]:
        with Session(self.engine) as session:
            statement = select(User)
            results = session.exec(statement)
            return list(results)

    async def get_user_by_id(self, user_id: UUID) -> User:
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()
            return user

    async def get_user_id_by_name(self, name: str) -> User:
        # There's no check right now for users with the same name, but we should figure out how to make the searching more robust
        with Session(self.engine) as session:
            statement = select(User).where(User.name == name)
            user = session.exec(statement).one()
            return user

    async def update_user(self, updated_user: User) -> User:
        user = await self.add_user(updated_user)
        return user
            

    async def delete_user(self, user_id: UUID) -> None:
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()
            session.delete(user)
            session.commit()


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
