
import one_line_day_py.src.data.json_back as module

from one_line_day_py.src.model import JournalEntry
from datetime import date, timedelta
from pathlib import Path
import json
import asyncio
from pytest import fixture

N = 2
MESSAGE_FORMAT = "This is mesage {i}"
PHOTO_FORMAT = "{i}.png"
# Ease of use
JsonDb = module.JsonDb


@fixture(scope="function")
def empty_db(tmp_path)->JsonDb:
    db_path = tmp_path / "db.json"
    return JsonDb(db_path)

    
@fixture(scope="function")
def filled_db(tmp_path)->JsonDb:
    db_path = tmp_path / "db.json"
    db = JsonDb(db_path)

    entries = (JournalEntry(date=date.today()+timedelta(days=1*i), message=format(), photos=[f]) for i in range(N))
    asyncio.gather((db.insert(entry) for entry in entries))

    return db

class TestJsonDb:

    def test_insert(self, empty_db):
        entry = JournalEntry(date=date.today(), message="A new message", photos=["a.png"])
        asyncio.run(empty_db.insert(entry))

        assert Path(empty_db.db_path).exists

        with open(empty_db.db_path, "r") as f:
            written_db = json.load(f)

        assert written_db == empty_db.serialize()

    def test_list(self, filled_db):
        entries = asyncio.run(filled_db.list())
        
        assert len(entries)==N

        for entry in entries:
            assert entry.message == 

    def test_get(self):
        pass

    def test_update(self):
        pass

    def test_delete(self):
        pass

    def test_write_file(self):
        pass

    def test_serialize_db(self):
        pass