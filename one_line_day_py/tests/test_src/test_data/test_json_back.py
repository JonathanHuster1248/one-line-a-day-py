import one_line_day_py.src.data.json_back as module

from one_line_day_py.src.model import JournalEntry
from datetime import date, timedelta
from pathlib import Path
import json
import asyncio
from uuid import uuid4, UUID

import pytest
from pytest import fixture
from litestar.exceptions import NotFoundException

N = 2
MESSAGE_FORMAT = "This is mesage {i}"
PHOTO_FORMAT = "{i}.png"
# Ease of use
JsonDb = module.JsonDb


@fixture(scope="function")
def empty_db(tmp_path) -> JsonDb:
    db_path = tmp_path / "db.json"
    return JsonDb(db_path)


@fixture(scope="function")
def filled_db(tmp_path) -> JsonDb:
    db_path = tmp_path / "db.json"
    db = JsonDb(db_path)

    for entry in (
        JournalEntry(
            date=date.today() + timedelta(days=1 * i),
            message=MESSAGE_FORMAT.format(i=i),
            photos=[PHOTO_FORMAT.format(i=i)],
        )
        for i in range(N)
    ):
        asyncio.run(db.insert(entry))

    return db


def get_first_entry(db: JsonDb) -> tuple[UUID, JournalEntry]:
    id = list(db.db.keys())[0]
    entry = db.db[id]

    return id, entry


class TestJsonDb:
    def test_insert(self, empty_db):
        entry = JournalEntry(
            date=date.today(), message="A new message", photos=["a.png"]
        )
        asyncio.run(empty_db.insert(entry))

        # TODO: we should just mock the write and ensure it was called
        assert Path(empty_db.db_path).exists

        with open(empty_db.db_path, "r") as f:
            written_db = json.load(f)

        assert written_db == empty_db.serialize()

    def test_list(self, filled_db):
        entries = asyncio.run(filled_db.list())

        assert len(entries) == N

        for entry in entries:
            assert MESSAGE_FORMAT.removesuffix("{i}") in entry.message
            assert all(
                PHOTO_FORMAT.removeprefix("{i}") in photo for photo in entry.photos
            )

    def test_get(self, filled_db):
        for key in filled_db.db.keys():
            entry = asyncio.run(filled_db.get(key))
            assert type(entry) is JournalEntry

        with pytest.raises(NotFoundException):
            asyncio.run(filled_db.get(uuid4()))

    def test_update(self, filled_db):
        id, original_entry = get_first_entry(filled_db)

        modified_entry = original_entry.model_copy(
            update={"message": "a modified message"}
        )

        asyncio.run(filled_db.update(id, modified_entry))

        updated_entry = filled_db.db[id]

        assert updated_entry.message == "a modified message"
        assert updated_entry.date == original_entry.date
        assert updated_entry.photos == original_entry.photos

        with pytest.raises(NotFoundException):
            asyncio.run(filled_db.update(uuid4(), modified_entry))

    def test_delete(self, filled_db):
        id, _ = get_first_entry(filled_db)
        asyncio.run(filled_db.delete(id))

        assert id not in filled_db.db

    def test_write_file(self, filled_db):
        asyncio.run(filled_db.write_file())

        assert Path(filled_db.db_path).exists

        read_back = JsonDb.read_db_with_default(filled_db.db_path)
        for id in read_back:
            assert id in filled_db.db
            assert read_back.get(id) == filled_db.db.get(id)

    def test_serialize_db(self, filled_db):
        serialized = filled_db.serialize()
        json.dumps(serialized)  # Raises no error
