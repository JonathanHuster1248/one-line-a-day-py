from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import event, extract
from sqlmodel import Session, SQLModel, col, create_engine, func, select

from ..exceptions import AttachmentLimitExceeded
from ..model import Attachment, JournalEntry, User

MAX_ATTACHMENTS_PER_ENTRY = 5  # keep in sync with frontend/src/config.ts


def init_db(db_path: Path):
    # SQLite creates the file but not its directory; a fresh DB_PATH may point
    # somewhere that doesn't exist yet.
    db_path.parent.mkdir(parents=True, exist_ok=True)
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

    async def delete_user(self, user_id: UUID) -> list[UUID]:
        """Delete the user; their entries and attachment rows go via ON DELETE CASCADE.

        Returns the deleted entry ids so the caller can remove their files.
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).one()
            entry_ids = list(
                session.exec(
                    select(JournalEntry.id).where(JournalEntry.author_id == user_id)
                )
            )
            session.delete(user)
            session.commit()
            return entry_ids


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


class AttachmentDb:
    """Attachment metadata rows. Used only by `AttachmentService`, never by a controller."""

    def __init__(self, db_path: Path):
        self.engine = init_db(db_path)

    async def add_attachment(self, attachment: Attachment) -> Attachment:
        """Count check and insert share one session; raises AttachmentLimitExceeded."""
        with Session(self.engine) as session:
            count = session.exec(
                select(func.count())
                .select_from(Attachment)
                .where(Attachment.entry_id == attachment.entry_id)
            ).one()
            if count >= MAX_ATTACHMENTS_PER_ENTRY:
                raise AttachmentLimitExceeded()
            session.add(attachment)
            session.commit()
            session.refresh(attachment)
            return attachment

    async def get_scoped(
        self, attachment_id: UUID, entry_id: UUID, author_id: UUID
    ) -> Attachment | None:
        """The one place that decides whether a user may touch an attachment."""
        with Session(self.engine) as session:
            statement = select(Attachment).where(
                Attachment.id == attachment_id,
                Attachment.entry_id == entry_id,
                Attachment.author_id == author_id,
            )
            return session.exec(statement).one_or_none()

    async def list_for_entry(self, entry_id: UUID, author_id: UUID) -> list[Attachment]:
        return (await self.list_for_entries([entry_id], author_id))[entry_id]

    async def list_for_entries(
        self, entry_ids: list[UUID], author_id: UUID
    ) -> dict[UUID, list[Attachment]]:
        """Every requested entry id is a key, with an empty list when it has none."""
        by_entry: dict[UUID, list[Attachment]] = {
            entry_id: [] for entry_id in entry_ids
        }
        if not entry_ids:
            return by_entry
        with Session(self.engine) as session:
            statement = (
                select(Attachment)
                .where(
                    col(Attachment.entry_id).in_(entry_ids),
                    Attachment.author_id == author_id,
                )
                .order_by(col(Attachment.created_at))
            )
            for attachment in session.exec(statement):
                by_entry[attachment.entry_id].append(attachment)
        return by_entry

    async def delete(self, attachment_id: UUID) -> None:
        with Session(self.engine) as session:
            attachment = session.exec(
                select(Attachment).where(Attachment.id == attachment_id)
            ).one()
            session.delete(attachment)
            session.commit()

    async def count_for_entry(self, entry_id: UUID) -> int:
        with Session(self.engine) as session:
            return session.exec(
                select(func.count())
                .select_from(Attachment)
                .where(Attachment.entry_id == entry_id)
            ).one()

    async def existing_entry_ids(self, entry_ids: list[UUID]) -> set[UUID]:
        """Which of the given ids are still journal entries (for the orphan sweep)."""
        if not entry_ids:
            return set()
        with Session(self.engine) as session:
            statement = select(JournalEntry.id).where(
                col(JournalEntry.id).in_(entry_ids)
            )
            return set(session.exec(statement))
