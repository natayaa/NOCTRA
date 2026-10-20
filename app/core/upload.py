"""Safe file upload handling.

Stores files under `media/` at the project root — separate from the
`app/static/` mount so user content never mixes with shipped assets.
Files are named `<uuid>.<ext>` and validated against a strict whitelist.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import ValidationError

# Decompression-bomb guard (Pillow defaults to ~89M px which is generous).
Image.MAX_IMAGE_PIXELS = 40_000_000  # ~40 MP

BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_ROOT = BASE_DIR / settings.MEDIA_ROOT
INQUIRY_UPLOAD_DIR = MEDIA_ROOT / "inquiries"

ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
EXT_FORMAT: dict[str, str] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".gif": "GIF",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_UPLOAD = 5


def ensure_dirs() -> None:
    INQUIRY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _is_valid_image(data: bytes) -> bool:
    """Magic-byte check for JPEG / PNG / GIF / WebP."""
    if len(data) < 12:
        return False
    if data[:3] == b"\xff\xd8\xff":                      # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":                 # PNG
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):               # GIF
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":    # WebP
        return True
    return False


def _strip_exif(data: bytes, expected_fmt: str) -> bytes:
    """Re-encode to strip EXIF. Preserves animation for GIF/WEBP."""
    try:
        img = Image.open(BytesIO(data))
        detected = (img.format or "").upper()
        if detected != expected_fmt:
            raise ValidationError(
                f"Extension says {expected_fmt} but file is {detected or 'unknown'}"
            )

        # Re-encoding an animated image frame-by-frame would drop the frames.
        # GIFs/WEBPs rarely carry EXIF in practice — pass through untouched.
        if getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1:
            return data

        # JPEG can't store RGBA/P — flatten to RGB.
        if detected == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        out = BytesIO()
        save_kwargs: dict = {}
        if detected in ("JPEG", "WEBP"):
            save_kwargs = {"quality": 88, "optimize": True}
        elif detected == "PNG":
            save_kwargs = {"optimize": True}

        img.save(out, format=detected, **save_kwargs)
        result = out.getvalue()
        if not _is_valid_image(result):
            raise ValidationError("Re-encoded output is not a valid image")
        return result
    except UnidentifiedImageError as exc:
        raise ValidationError("File is not a valid image") from exc
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(f"Could not process image: {exc}") from exc


def _safe_extension(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type {ext or '(none)'} not allowed. "
            f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return ext


async def save_inquiry_photo(file: UploadFile) -> str:
    """Persist one uploaded photo. Returns the public URL path."""
    ensure_dirs()

    ext = _safe_extension(file)
    contents = await file.read()

    if not contents:
        raise ValidationError("File is empty")
    if len(contents) > MAX_FILE_SIZE:
        raise ValidationError(
            f"File too large ({len(contents) // 1024} KB). "
            f"Max is {MAX_FILE_SIZE // (1024 * 1024)} MB."
        )
    if not _is_valid_image(contents):
        raise ValidationError("File does not appear to be a valid image")

    # Re-encode off the event loop — PIL is CPU-bound.
    stripped = await asyncio.to_thread(_strip_exif, contents, EXT_FORMAT[ext])

    now = datetime.now(UTC)
    sub_dir = INQUIRY_UPLOAD_DIR / f"{now.year:04d}" / f"{now.month:02d}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    full_path = sub_dir / filename
    await asyncio.to_thread(full_path.write_bytes, stripped)

    rel = full_path.relative_to(MEDIA_ROOT).as_posix()
    return f"/media/{rel}"


async def save_inquiry_photos(files: list[UploadFile]) -> list[dict]:
    """Save up to MAX_FILES_PER_UPLOAD photos. Returns metadata dicts."""
    real_files = [f for f in files if f and f.filename]

    if len(real_files) > MAX_FILES_PER_UPLOAD:
        raise ValidationError(
            f"At most {MAX_FILES_PER_UPLOAD} photos allowed per inquiry"
        )

    results = []
    for i, f in enumerate(real_files):
        path = await save_inquiry_photo(f)
        results.append({
            "file_path": path,
            "file_name": f.filename,
            "is_primary": i == 0,
        })
    return results