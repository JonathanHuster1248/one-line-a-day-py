from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from one_line_day_py.src.data.db import init_db
from one_line_day_py.src.model import Attachment, AttachmentKind, JournalEntry, User


@pytest.fixture
def engine(tmp_path):
    return init_db(tmp_path / "test.db")


def _user_and_entry(session):
    user = User(name="Alice", email="alice@example.com", hashed_password="x")
    session.add(user)
    session.commit()
    entry = JournalEntry(author_id=user.id, date=date(2024, 1, 1), message="hi")
    session.add(entry)
    session.commit()
    return user, entry


def _attachment(user, entry):
    return Attachment(
        entry_id=entry.id,
        author_id=user.id,
        filename="a.png",
        kind=AttachmentKind.IMAGE,
        content_type="image/webp",
        size_bytes=10,
        has_thumbnail=True,
    )


def test_foreign_keys_pragma_is_on_for_new_connections(engine):
    for _ in range(2):
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_foreign_keys_are_enforced(engine):
    with Session(engine) as session:
        session.add(JournalEntry(author_id=uuid4(), date=date(2024, 1, 1), message="x"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_entry_cascades_to_attachments(engine):
    with Session(engine) as session:
        user, entry = _user_and_entry(session)
        session.add(_attachment(user, entry))
        session.add(_attachment(user, entry))
        session.commit()
        assert len(session.exec(select(Attachment)).all()) == 2

        session.delete(entry)
        session.commit()
        assert session.exec(select(Attachment)).all() == []


def test_deleting_user_cascades_to_entries_and_attachments(engine):
    with Session(engine) as session:
        user, entry = _user_and_entry(session)
        session.add(_attachment(user, entry))
        session.commit()

        session.delete(user)
        session.commit()
        assert session.exec(select(JournalEntry)).all() == []
        assert session.exec(select(Attachment)).all() == []


def test_init_db_creates_missing_parent_directories(tmp_path):
    db_path = tmp_path / "does" / "not" / "exist" / "test.db"

    engine = init_db(db_path)

    with Session(engine) as session:
        assert session.exec(select(User)).all() == []
    assert db_path.is_file()


def test_attachment_defaults(engine):
    with Session(engine) as session:
        user, entry = _user_and_entry(session)
        session.add(_attachment(user, entry))
        session.commit()
        saved = session.exec(select(Attachment)).one()
        assert saved.created_at is not None
        assert saved.width is None and saved.taken_at is None
