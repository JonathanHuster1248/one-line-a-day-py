import io
from dataclasses import dataclass
from datetime import datetime

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

from .exceptions import AttachmentProcessingError

pillow_heif.register_heif_opener()

THUMB_SIZE = 320
DISPLAY_MAX_EDGE = 2048
THUMB_QUALITY = 80
DISPLAY_QUALITY = 85

# EXIF tag IDs, from the EXIF/TIFF specs (also in PIL.ExifTags.Base).
# "ExifOffset" (0x8769): pointer to the Exif sub-IFD, where most camera
# metadata lives; read with `getexif().get_ifd(...)`.
_EXIF_IFD = 0x8769
# "DateTimeOriginal" (0x9003, in the Exif sub-IFD): when the photo was taken
# ("YYYY:MM:DD HH:MM:SS", no timezone).
_EXIF_DATETIME_ORIGINAL = 0x9003
# "DateTime" (0x0132, in the main IFD): file last-modified time; the fallback
# when DateTimeOriginal is missing.
_EXIF_DATETIME = 0x0132


@dataclass(frozen=True)
class ProcessedImage:
    thumb: bytes
    display: bytes
    width: int  # of the display copy
    height: int
    taken_at: datetime | None


def _taken_at(img: Image.Image) -> datetime | None:
    try:
        exif = img.getexif()
        raw = exif.get_ifd(_EXIF_IFD).get(_EXIF_DATETIME_ORIGINAL) or exif.get(
            _EXIF_DATETIME
        )
        if not raw:
            return None
        return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError, KeyError, AttributeError, SyntaxError):
        # malformed _metadata_ must never fail an upload
        return None


def _to_webp(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality)
    return buf.getvalue()


def process_image(data: bytes) -> ProcessedImage:
    """Decode once and derive a 320x320 cover-crop thumbnail and a 2048px display copy.

    Raises AttachmentProcessingError for anything that can't be decoded; the
    underlying exception text is deliberately not propagated (it may leak content).
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.seek(0)  # first frame of animated inputs
            taken_at = _taken_at(img)
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

            thumb = ImageOps.fit(
                img, (THUMB_SIZE, THUMB_SIZE), method=Image.Resampling.LANCZOS
            )

            display = img.copy()
            display.thumbnail(
                (DISPLAY_MAX_EDGE, DISPLAY_MAX_EDGE), Image.Resampling.LANCZOS
            )
            return ProcessedImage(
                thumb=_to_webp(thumb, THUMB_QUALITY),
                display=_to_webp(display, DISPLAY_QUALITY),
                width=display.width,
                height=display.height,
                taken_at=taken_at,
            )
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
        Image.DecompressionBombError,
    ) as exc:
        raise AttachmentProcessingError() from exc
