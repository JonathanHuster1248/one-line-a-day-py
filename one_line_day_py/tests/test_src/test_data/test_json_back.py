
import one_line_day_py.src.data.json_back as module

from one_line_day_py.src.model import JournalEntry
from datetime import date
from pathlib import Path
import json
import asyncio

# TODO: Mock the settings and env so we can ensure we don't overwrite any data

class TestJsonDb:

    def test_insert(self):
        entry = JournalEntry(date=date.today(), message="A new message", photos=["a.png"])
        asyncio.run(module.JsonDb.insert(entry))

        file_path = module.JsonDb.db_path
        assert Path(file_path).exists

        with open(file_path, "r") as f:
            written_db = json.load(f)

        assert written_db == module.JsonDb.serialize_db(module.JsonDb.db)

    def test_list(self):
        pass

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