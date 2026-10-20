import ast
import inspect
import io
from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from PIL import Image

from one_line_day_py.main import make_app
from one_line_day_py.src.controllers import journal
from one_line_day_py.src.data.db import JournalDb


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "red").save(buf, format="PNG")
    return buf.getvalue()


def entry_dir(app: Litestar, entry_id: str) -> Path:
    return app.state.attachment_service.storage.root / entry_id


@pytest.fixture
def alice_client(app: Litestar, alice):
    with TestClient(app=app) as c:
        c.post("/auth/signup", json=alice)
        yield c


@pytest.fixture
def entry_with_attachment(alice_client) -> tuple[str, dict]:
    entry_id = alice_client.post("/journals/?date=2026-01-01&message=hi").json()["id"]
    attachment = alice_client.post(
        f"/journals/{entry_id}/attachments/",
        files={"file": ("photo.png", png(), "image/png")},
    ).json()
    return entry_id, attachment


def test_create_returns_empty_attachments(alice_client) -> None:
    response = alice_client.post("/journals/?date=2026-01-01&message=hi")

    assert response.status_code == 201
    assert response.json()["attachments"] == []
    assert response.json()["attachments_available"] is True


def test_list_includes_attachments(alice_client, entry_with_attachment) -> None:
    entry_id, attachment = entry_with_attachment
    alice_client.post("/journals/?date=2025-01-01&message=bare")

    response = alice_client.get("/journals/?month=1&day=1")

    by_id = {e["id"]: e for e in response.json()}
    assert by_id[entry_id]["attachments"] == [attachment]
    assert by_id[entry_id]["attachments_available"] is True
    assert [e["attachments"] for e in by_id.values() if e["id"] != entry_id] == [[]]


def test_get_includes_attachments(alice_client, entry_with_attachment) -> None:
    entry_id, attachment = entry_with_attachment

    response = alice_client.get(f"/journals/{entry_id}")

    assert response.json()["attachments"] == [attachment]


def test_update_includes_attachments(alice_client, entry_with_attachment) -> None:
    entry_id, attachment = entry_with_attachment

    response = alice_client.put(f"/journals/{entry_id}?message=edited")

    assert response.json()["message"] == "edited"
    assert response.json()["attachments"] == [attachment]


def test_delete_entry_cascades_rows_and_removes_directory(
    app, alice_client, entry_with_attachment
) -> None:
    entry_id, attachment = entry_with_attachment
    assert entry_dir(app, entry_id).is_dir()

    response = alice_client.delete(f"/journals/{entry_id}")

    assert response.status_code == 204
    assert not entry_dir(app, entry_id).exists()
    base = f"/journals/{entry_id}/attachments"
    assert alice_client.get(f"{base}/").json() == []
    assert alice_client.get(f"{base}/{attachment['id']}/content").status_code == 404


def test_delete_entry_succeeds_when_file_removal_fails_and_sweep_cleans_up(
    app, alice_client, entry_with_attachment, monkeypatch
) -> None:
    entry_id, _ = entry_with_attachment

    def broken(_entry_id):
        raise OSError("disk on fire")

    with monkeypatch.context() as m:
        m.setattr(app.state.attachment_service.storage, "delete_entry", broken)
        response = alice_client.delete(f"/journals/{entry_id}")

    assert response.status_code == 204
    assert entry_dir(app, entry_id).is_dir()

    # The next startup's orphan sweep removes the leftover directory.
    with TestClient(app=make_app()):
        pass
    assert not entry_dir(app, entry_id).exists()


def test_entries_still_returned_when_attachment_lookup_fails(
    app, alice_client, entry_with_attachment, monkeypatch
) -> None:
    entry_id, _ = entry_with_attachment

    async def broken(*_args):
        raise RuntimeError("db gone")

    monkeypatch.setattr(app.state.attachment_service, "list_for_entries", broken)

    for response in (
        alice_client.get("/journals/"),
        alice_client.get(f"/journals/{entry_id}"),
        alice_client.put(f"/journals/{entry_id}?message=edited"),
    ):
        assert response.status_code == 200
        body = response.json()
        for entry in body if isinstance(body, list) else [body]:
            assert entry["attachments"] == []
            assert entry["attachments_available"] is False


def _imported_modules(source: str) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


ATTACHMENT_MODULES = ("attachment", "images", "services")


def test_journal_controller_imports_no_attachment_modules() -> None:
    imported = _imported_modules(inspect.getsource(journal))

    offenders = {
        name
        for name in imported
        if any(part in name.lower() for part in ATTACHMENT_MODULES)
        # The protocol's own value type is the one allowed attachment name.
        and name != "model.AttachmentPublic"
    }
    assert offenders == set()


def test_journal_db_names_nothing_attachment_related() -> None:
    assert "attachment" not in inspect.getsource(JournalDb).lower()
