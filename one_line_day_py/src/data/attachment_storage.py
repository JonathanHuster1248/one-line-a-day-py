import logging
import os
import shutil
import tempfile
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from ..exceptions import StorageUnavailable

logger = logging.getLogger(__name__)


class Variant(StrEnum):
    THUMB = "thumb"
    DISPLAY = "display"
    PDF = "pdf"

_SUFFIXES = {
    Variant.THUMB: "thumb.webp",
    Variant.DISPLAY: "display.webp",
    Variant.PDF: "pdf",
}


class AttachmentStorage:
    """Owns the attachments directory: `{root}/{entry_id}/{attachment_id}.{variant}`.

    Paths are built only from UUIDs and a fixed variant suffix, never from
    user-supplied values. The root is created lazily on the first write, and a
    missing or unwritable root only matters (raises) when writing.
    """

    def __init__(self, root: Path):
        self.root = root

    def _entry_dir(self, entry_id: UUID) -> Path:
        return self.root / str(entry_id)

    def _file(self, entry_id: UUID, attachment_id: UUID, variant: Variant) -> Path:
        return self._entry_dir(entry_id) / f"{attachment_id}.{_SUFFIXES[variant]}"

    def save(
        self, entry_id: UUID, attachment_id: UUID, variant: Variant, data: bytes
    ) -> Path:
        """Write via a temp file and rename so a half-written file is never served."""
        target = self._file(entry_id, attachment_id, variant)
        tmp_name = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_name, target)
        except OSError as exc:
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)
            logger.error("Attachment write failed: %s", type(exc).__name__)
            raise StorageUnavailable() from exc
        return target

    def path_for(
        self, entry_id: UUID, attachment_id: UUID, variant: Variant
    ) -> Path | None:
        path = self._file(entry_id, attachment_id, variant)
        return path if path.is_file() else None

    def delete_attachment(self, entry_id: UUID, attachment_id: UUID) -> None:
        for variant in Variant:
            self._file(entry_id, attachment_id, variant).unlink(missing_ok=True)
        try:
            # If this was the only attachment, delete the orphaned directory. If there are other attachments, it will error and stay
            self._entry_dir(entry_id).rmdir()  
        except OSError:
            pass

    def delete_entry(self, entry_id: UUID) -> None:
        shutil.rmtree(self._entry_dir(entry_id), ignore_errors=True)

    def entry_dirs(self) -> list[UUID]:
        """Entry IDs that have a directory on disk (for the orphan sweep)."""
        try:
            children = list(self.root.iterdir())
        except OSError:
            return []
        ids = []
        for child in children:
            if not child.is_dir():
                continue
            try:
                ids.append(UUID(child.name))
            except ValueError:
                continue
        return ids
