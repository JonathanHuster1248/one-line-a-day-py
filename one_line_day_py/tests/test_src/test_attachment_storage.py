import os
from uuid import uuid4

import pytest

from one_line_day_py.src.data.attachment_storage import (
    TRASH_DIR,
    AttachmentStorage,
    Variant,
)
from one_line_day_py.src.exceptions import StorageUnavailable


@pytest.fixture
def storage(tmp_path):
    return AttachmentStorage(tmp_path / "root")


def test_round_trip(storage):
    entry_id, att_id = uuid4(), uuid4()
    saved = storage.save(entry_id, att_id, Variant.THUMB, b"abc")
    assert storage.path_for(entry_id, att_id, Variant.THUMB) == saved
    assert saved.read_bytes() == b"abc"
    assert saved == storage.root / str(entry_id) / f"{att_id}.thumb.webp"


def test_root_is_created_lazily(tmp_path):
    root = tmp_path / "nested" / "root"
    storage = AttachmentStorage(root)
    assert not root.exists()
    assert storage.path_for(uuid4(), uuid4(), Variant.PDF) is None
    storage.save(uuid4(), uuid4(), Variant.PDF, b"x")
    assert root.is_dir()


def test_missing_file_returns_none(storage):
    assert storage.path_for(uuid4(), uuid4(), Variant.DISPLAY) is None


def test_save_leaves_no_temp_files(storage):
    entry_id = uuid4()
    storage.save(entry_id, uuid4(), Variant.DISPLAY, b"x")
    assert [p.suffix for p in (storage.root / str(entry_id)).iterdir()] == [".webp"]


def test_delete_one_keeps_others(storage):
    entry_id, a, b = uuid4(), uuid4(), uuid4()
    for att in (a, b):
        storage.save(entry_id, att, Variant.THUMB, b"t")
        storage.save(entry_id, att, Variant.DISPLAY, b"d")
    storage.delete_attachment(entry_id, a)
    assert storage.path_for(entry_id, a, Variant.THUMB) is None
    assert storage.path_for(entry_id, a, Variant.DISPLAY) is None
    assert storage.path_for(entry_id, b, Variant.THUMB) is not None


def test_delete_last_attachment_removes_entry_dir(storage):
    entry_id, a = uuid4(), uuid4()
    storage.save(entry_id, a, Variant.PDF, b"x")
    storage.delete_attachment(entry_id, a)
    assert not (storage.root / str(entry_id)).exists()


def test_delete_entry(storage):
    entry_id, other = uuid4(), uuid4()
    storage.save(entry_id, uuid4(), Variant.PDF, b"x")
    storage.save(other, uuid4(), Variant.PDF, b"x")
    storage.delete_entry(entry_id)
    assert not (storage.root / str(entry_id)).exists()
    assert (storage.root / str(other)).exists()


def test_delete_missing_is_a_noop(storage):
    storage.delete_entry(uuid4())
    storage.delete_attachment(uuid4(), uuid4())


def test_entry_dirs_lists_only_uuid_dirs(storage):
    a, b = uuid4(), uuid4()
    storage.save(a, uuid4(), Variant.PDF, b"x")
    storage.save(b, uuid4(), Variant.PDF, b"x")
    (storage.root / "not-a-uuid").mkdir()
    (storage.root / str(uuid4())).write_text("a file, not a dir")
    assert set(storage.entry_dirs()) == {a, b}


def test_entry_dirs_with_missing_root(storage):
    assert storage.entry_dirs() == []


def test_path_never_contains_user_supplied_values(storage):
    entry_id, att_id = uuid4(), uuid4()
    path = storage.save(entry_id, att_id, Variant.DISPLAY, b"x")
    assert path.relative_to(storage.root).parts == (
        str(entry_id),
        f"{att_id}.display.webp",
    )


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_root_raises_on_write_only(tmp_path):
    root = tmp_path / "ro"
    root.mkdir()
    root.chmod(0o500)
    try:
        storage = AttachmentStorage(root)
        assert storage.path_for(uuid4(), uuid4(), Variant.PDF) is None
        assert storage.entry_dirs() == []
        storage.delete_entry(uuid4())
        with pytest.raises(StorageUnavailable):
            storage.save(uuid4(), uuid4(), Variant.PDF, b"x")
    finally:
        root.chmod(0o700)


def test_root_that_is_a_file_raises_on_write(tmp_path):
    root = tmp_path / "file"
    root.write_text("x")
    with pytest.raises(StorageUnavailable):
        AttachmentStorage(root).save(uuid4(), uuid4(), Variant.PDF, b"x")


def test_trash_entry_moves_directory_and_never_overwrites(storage):
    entry_id, first, second = uuid4(), uuid4(), uuid4()
    storage.save(entry_id, first, Variant.PDF, b"1")
    storage.trash_entry(entry_id)
    storage.save(entry_id, second, Variant.PDF, b"2")

    moved = storage.trash_entry(entry_id)

    assert not (storage.root / str(entry_id)).exists()
    assert moved.name.startswith(f"{entry_id}-")
    trash = storage.root / TRASH_DIR
    assert (trash / str(entry_id) / f"{first}.pdf").read_bytes() == b"1"
    assert (moved / f"{second}.pdf").read_bytes() == b"2"
    # The trash itself is never mistaken for an entry directory.
    assert storage.entry_dirs() == []
