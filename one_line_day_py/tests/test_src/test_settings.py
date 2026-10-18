import pytest

from one_line_day_py.src.settings import (
    DEFAULT_ATTACHMENTS_PATH,
    DEFAULT_DB_PATH,
    CoreSettings,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    monkeypatch.delenv("ATTACHMENTS_PATH", raising=False)


def test_attachments_path_defaults_to_sibling_of_default_db():
    assert CoreSettings().attachments_path == DEFAULT_ATTACHMENTS_PATH
    assert DEFAULT_ATTACHMENTS_PATH.parent == DEFAULT_DB_PATH.parent
    assert DEFAULT_ATTACHMENTS_PATH.name == "attachments"


def test_attachments_path_can_be_set_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ATTACHMENTS_PATH", str(tmp_path / "photos"))
    assert CoreSettings().attachments_path == tmp_path / "photos"


def test_overriding_db_path_does_not_move_attachments(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "elsewhere" / "db.sqlite"))
    settings = CoreSettings()
    assert settings.db_path == tmp_path / "elsewhere" / "db.sqlite"
    assert settings.attachments_path == DEFAULT_ATTACHMENTS_PATH


def test_overriding_attachments_path_does_not_move_db(monkeypatch, tmp_path):
    monkeypatch.setenv("ATTACHMENTS_PATH", str(tmp_path / "photos"))
    settings = CoreSettings()
    assert settings.db_path == DEFAULT_DB_PATH
    assert settings.attachments_path == tmp_path / "photos"
