import pytest
from litestar.testing import TestClient

import one_line_day_py.src.dependencies as dependencies
from one_line_day_py.main import make_app
from one_line_day_py.src.data.db import JournalDb, UserDb
from one_line_day_py.src.settings import settings


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(dependencies, "users_db", UserDb(db_path))
    monkeypatch.setattr(dependencies, "journals_db", JournalDb(db_path))
    return make_app()


@pytest.fixture
def client(app):
    with TestClient(app=app) as c:
        yield c


@pytest.fixture
def alice():
    return {"name": "Alice", "email": "alice@example.com", "password": "hunter22"}


@pytest.fixture
def bob():
    return {"name": "Bob", "email": "bob@example.com", "password": "correct-horse"}
