import io
import logging
import logging.config

import pytest
from PIL import Image

from one_line_day_py.src import logging_config
from one_line_day_py.src.images import process_image
from one_line_day_py.src.settings import settings


def exif_jpeg() -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "EXIF-MAKE-MARKER"
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "red").save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def debug_config(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "log_level", "DEBUG")
    monkeypatch.setattr(settings, "db_path", tmp_path / "db.sqlite")
    return logging_config.create_logging_config()


def test_image_library_loggers_stay_at_warning_under_debug(debug_config) -> None:
    for name in logging_config.IMAGE_LIBRARY_LOGGERS:
        assert debug_config.loggers[name]["level"] == "WARNING"


def test_exif_values_not_logged_under_debug(debug_config, caplog) -> None:
    # Apply only the logger levels, not the handlers, to keep global state small.
    previous = {
        n: logging.getLogger(n).level for n in logging_config.IMAGE_LIBRARY_LOGGERS
    }
    logging.config.dictConfig(
        {
            "version": 1,
            "incremental": True,
            "loggers": {
                n: debug_config.loggers[n] for n in logging_config.IMAGE_LIBRARY_LOGGERS
            },
        }
    )
    try:
        with caplog.at_level(logging.DEBUG):
            process_image(exif_jpeg())
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)

    assert "EXIF-MAKE-MARKER" not in caplog.text
