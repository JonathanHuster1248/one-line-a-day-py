import io
from datetime import datetime

import pillow_heif
import pytest
from PIL import Image

from one_line_day_py.src.exceptions import AttachmentProcessingError
from one_line_day_py.src.images import process_image


def _encode(img, fmt, **kwargs):
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _open(data):
    return Image.open(io.BytesIO(data))


@pytest.mark.parametrize("size", [(800, 400), (400, 800), (500, 500), (100, 60)])
def test_thumbnail_is_always_320_square_webp(size):
    result = process_image(_encode(Image.new("RGB", size, "red"), "JPEG"))
    thumb = _open(result.thumb)
    assert thumb.format == "WEBP"
    assert thumb.size == (320, 320)


def test_display_fits_2048_and_keeps_aspect():
    result = process_image(_encode(Image.new("RGB", (4096, 2048), "blue"), "PNG"))
    display = _open(result.display)
    assert display.format == "WEBP"
    assert display.size == (2048, 1024)
    assert (result.width, result.height) == (2048, 1024)


def test_small_image_is_not_upscaled_in_display():
    result = process_image(_encode(Image.new("RGB", (100, 50), "blue"), "PNG"))
    assert _open(result.display).size == (100, 50)


def test_exif_orientation_is_applied():
    img = Image.new("RGB", (200, 100), "green")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise to display
    result = process_image(_encode(img, "JPEG", exif=exif))
    assert (result.width, result.height) == (100, 200)


def test_gif_uses_first_frame():
    frames = [Image.new("RGB", (60, 40), c) for c in ("red", "blue")]
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:])
    result = process_image(buf.getvalue())
    assert (result.width, result.height) == (60, 40)
    px = _open(result.display).convert("RGB").getpixel((30, 20))
    assert px[0] > 200 and px[2] < 60  # red, not blue


def test_png_with_alpha_keeps_transparency():
    result = process_image(_encode(Image.new("RGBA", (50, 50), (255, 0, 0, 0)), "PNG"))
    assert _open(result.display).convert("RGBA").getpixel((10, 10))[3] == 0


def test_heic_is_decoded():
    heif = pillow_heif.from_pillow(Image.new("RGB", (64, 48), "purple"))
    buf = io.BytesIO()
    heif.save(buf, format="HEIF")
    result = process_image(buf.getvalue())
    assert (result.width, result.height) == (64, 48)
    assert _open(result.thumb).size == (320, 320)


def test_taken_at_is_extracted():
    img = Image.new("RGB", (50, 50))
    exif = Image.Exif()
    exif.get_ifd(0x8769)[0x9003] = "2023:07:04 12:30:15"
    result = process_image(_encode(img, "JPEG", exif=exif))
    assert result.taken_at == datetime(2023, 7, 4, 12, 30, 15)


def test_taken_at_missing_or_malformed_is_none():
    assert process_image(_encode(Image.new("RGB", (50, 50)), "PNG")).taken_at is None
    exif = Image.Exif()
    exif.get_ifd(0x8769)[0x9003] = "garbage"
    result = process_image(_encode(Image.new("RGB", (50, 50)), "JPEG", exif=exif))
    assert result.taken_at is None


def test_derived_files_carry_no_exif():
    exif = Image.Exif()
    exif.get_ifd(0x8769)[0x9003] = "2023:07:04 12:30:15"
    result = process_image(_encode(Image.new("RGB", (50, 50)), "JPEG", exif=exif))
    assert len(_open(result.display).getexif()) == 0


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG\r\n\x1a\ntruncated"])
def test_undecodable_input_raises(data):
    with pytest.raises(AttachmentProcessingError):
        process_image(data)


def test_error_does_not_leak_decoder_message():
    with pytest.raises(AttachmentProcessingError) as exc_info:
        process_image(b"secret-bytes")
    assert "secret" not in str(exc_info.value)
