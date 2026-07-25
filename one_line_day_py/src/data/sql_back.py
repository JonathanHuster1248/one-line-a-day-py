from uuid import UUID

from ..model import JournalEntry, User

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
        with Session(self.engine) as session:
            session.add(user)
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
        self.engine = init_db(db_path)

    async def add_entry(self, entry: JournalEntry) -> JournalEntry:
        with Session(self.engine) as session:
            session.add(entry)
            session.commit()
        return entry

    async def list_entries(self, **kwargs) -> list[JournalEntry]:
        with Session(self.engine) as session:
            statement = select(JournalEntry)
            entries = session.exec(statement)
            return list(entries)

    async def get_entry(self, entry_id: UUID) -> JournalEntry:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            user = session.exec(statement).one()
            return user

    async def get_entry_author(self, entry_id: UUID) -> UUID:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            user = session.exec(statement).one()
            return user.author_id

    async def update_entry(self, updated_entry: JournalEntry) -> JournalEntry:
        await self.add_entry(updated_entry)
        return updated_entry

    async def delete_journal(self, entry_id: UUID) -> None:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            entry = session.exec(statement).one()
            session.delete(entry)
            session.commit()
