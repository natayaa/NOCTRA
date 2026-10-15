"""Safe file upload handling.

Stores files under `media/` at the project root — separate from the
`app/static/` mount so user content never mixes with shipped assets.
Files are named `<uuid>.<ext>` and validated against a strict whitelist.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from PIL import Image
from io import BytesIO

from fastapi import UploadFile

from app.core.exceptions import ValidationError

BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_ROOT = BASE_DIR / "media"
INQUIRY_UPLOAD_DIR = MEDIA_ROOT / "inquiries"

ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_UPLOAD = 5


def ensure_dirs() -> None:
    INQUIRY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _strip_exif(data: bytes) -> bytes:
    try:
        img = Image.open(BytesIO(data))
        # Re-encode without EXIF
        out = BytesIO()
        fmt = img.format or "JPEG"
        # PIL akan strip EXIF kalau tidak di-pass sebagai parameter
        img.save(out, format=fmt, quality=88, optimize=True)
        return out.getvalue()
    except Exception:
        # Kalau gagal re-encode, tolak file
        raise ValidationError("Could not process image (corrupted EXIF?)")

def _safe_extension(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type {ext or '(none)'} not allowed. "
            f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


def _is_valid_image(data: bytes) -> bool:
    """
    Magic-byte check for JPEG / PNG / GIF / WebP.
    Replaces the deprecated `imghdr` module (removed in Python 3.13).
    """
    if len(data) < 12:
        return False

    # JPEG: FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return True

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True

    # GIF: "GIF87a" or "GIF89a"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True

    # WebP: "RIFF" + 4 bytes + "WEBP"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True

    return False


async def save_inquiry_photo(file: UploadFile) -> str:
    """
    Persist one uploaded photo. Returns the public URL path
    (e.g. /media/inquiries/2026/10/abc.jpg).
    """
    ensure_dirs()

    ext = _safe_extension(file)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise ValidationError(
            f"File too large ({len(contents) // 1024} KB). "
            f"Max is {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )
    if len(contents) == 0:
        raise ValidationError("File is empty")

    if not _is_valid_image(contents):
        raise ValidationError("File does not appear to be a valid image")

    now = datetime.now(UTC)
    sub_dir = INQUIRY_UPLOAD_DIR / f"{now.year:04d}" / f"{now.month:02d}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    _strip_exif(contents)
    full_path = sub_dir / filename
    full_path.write_bytes(contents)

    rel = full_path.relative_to(MEDIA_ROOT).as_posix()
    return f"/media/{rel}"


async def save_inquiry_photos(files: list[UploadFile]) -> list[dict]:
    """Save up to MAX_FILES_PER_UPLOAD photos. Returns metadata dicts."""
    real_files = [f for f in files if f and f.filename]

    if len(real_files) > MAX_FILES_PER_UPLOAD:
        raise ValidationError(f"At most {MAX_FILES_PER_UPLOAD} photos allowed per inquiry")

    results = []
    for i, f in enumerate(real_files):
        path = await save_inquiry_photo(f)
        results.append({
            "file_path": path,
            "file_name": f.filename,
            "is_primary": i == 0,
        })
    return results