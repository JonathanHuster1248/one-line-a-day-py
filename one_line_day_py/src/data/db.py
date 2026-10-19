from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import event, extract
from sqlmodel import Session, SQLModel, create_engine, select

from ..model import JournalEntry, User


def init_db(db_path: Path):
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        # SQLite ignores foreign keys (and ON DELETE CASCADE) unless enabled per connection.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


class UserDb:
    def __init__(self, db_path: Path):
        self.engine = init_db(db_path)

    async def add_user(self, user: User) -> User:
        with Session(self.engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
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

    async def get_user_by_name(self, name: str) -> User:
        # There's no check right now for users with the same name, but we should figure out how to make the searching more robust
        with Session(self.engine) as session:
            statement = select(User).where(User.name == name)
            user = session.exec(statement).one()
            return user

    async def get_user_by_email(self, email: str) -> User | None:
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).one_or_none()

    async def update_user(self, user_id: UUID, name: str | None = None) -> User:
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()

            if name is not None:
                user.name = name

            session.commit()
            session.refresh(user)

            return user

    async def delete_user(self, user_id: UUID) -> None:
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()
            session.delete(user)
            session.commit()


class JournalDb:
    def __init__(self, db_path: Path):
        self.engine = init_db(db_path)

    async def add_entry(self, entry: JournalEntry) -> JournalEntry:
        # TODO: Raise a 400 error when we get an integrety issue (author id not found or author id and date already exist)
        with Session(self.engine) as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    async def list_entries(
        self,
        author_id: UUID | None = None,
        month: int | None = None,
        day: int | None = None,
        year: int | None = None,
    ) -> list[JournalEntry]:
        with Session(self.engine) as session:
            statement = select(JournalEntry)
            if author_id:
                statement = statement.where(JournalEntry.author_id == author_id)
            if month:
                statement = statement.where(
                    extract("month", JournalEntry.date) == month
                )
            if day:
                statement = statement.where(extract("day", JournalEntry.date) == day)
            if year:
                statement = statement.where(extract("year", JournalEntry.date) == year)
            entries = session.exec(statement)
            return list(entries)

    async def get_entry(self, entry_id: UUID) -> JournalEntry:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            entry = session.exec(statement).one()
            return entry

    async def get_entry_author(self, entry_id: UUID) -> UUID:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            entry = session.exec(statement).one()
            return entry.author_id

    async def update_entry(
        self,
        entry_id: UUID,
        date: date | None = None,
        message: str | None = None,
    ) -> JournalEntry:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            entry = session.exec(statement).one()

            if date is not None:
                entry.date = date
            if message is not None:
                entry.message = message

            session.commit()
            session.refresh(entry)

            return entry

    async def delete_entry(self, entry_id: UUID) -> None:
        with Session(self.engine) as session:
            statement = select(JournalEntry).where(JournalEntry.id == entry_id)
            entry = session.exec(statement).one()
            session.delete(entry)
            session.commit()
