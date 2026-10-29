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
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 5
_READ_CHUNK = 64 * 1024


def ensure_dirs() -> None:
    INQUIRY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def remove_media_file(url_path: str | None) -> bool:
    """
    Delete a file previously stored under `MEDIA_ROOT`.

    Accepts the public path (`/media/inquiries/...`) recorded in the DB.
    Returns True when a file was removed. Paths that escape MEDIA_ROOT
    (traversal, absolute URLs, legacy rows) are ignored.
    """
    if not url_path:
        return False

    prefix = "/media/"
    if not url_path.startswith(prefix):
        return False

    try:
        root = MEDIA_ROOT.resolve()
        target = (MEDIA_ROOT / url_path[len(prefix):]).resolve()
        target.relative_to(root)  # raises ValueError outside the root
    except (OSError, ValueError):
        return False

    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        # A locked/permission-denied file must not break the request.
        return False



def _is_valid_image(data: bytes) -> bool:
    if len(data) < 12:
        return False
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def _strip_exif(data: bytes, expected_fmt: str) -> bytes:
    try:
        img = Image.open(BytesIO(data))
        detected = (img.format or "").upper()
        if detected != expected_fmt:
            raise ValidationError(
                f"Extension says {expected_fmt} but file is {detected or 'unknown'}"
            )

        if getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1:
            # Re-encoding frame-by-frame would drop animation; EXIF in
            # animated GIF/WEBP is rare in practice, so pass through.
            return data

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
        # Log-worthy detail is preserved in the chained exception; the
        # caller only sees a generic message so PIL internals don't leak.
        raise ValidationError("Could not process image") from exc


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

    # Stream-read with a hard cap — never buffer more than MAX_FILE_SIZE.
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await file.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise ValidationError(
                    f"File too large. Max is {MAX_FILE_SIZE // (1024 * 1024)} MB."
                )
            chunks.append(chunk)
    finally:
        # Starlette's UploadFile is not auto-closed — release the spool
        # file whether or not the read succeeded.
        await file.close()

    contents = b"".join(chunks)
    if not contents:
        raise ValidationError("File is empty")
    if not _is_valid_image(contents):
        raise ValidationError("File does not appear to be a valid image")

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
        # Close everything we were given so nothing leaks.
        for f in real_files:
            try:
                await f.close()
            except Exception:
                pass
        raise ValidationError(
            f"At most {MAX_FILES_PER_UPLOAD} photos allowed per inquiry"
        )

    results = []
    try:
        for i, f in enumerate(real_files):
            path = await save_inquiry_photo(f)
            results.append({
                "file_path": path,
                "file_name": f.filename,
                "is_primary": i == 0,
            })
    except Exception:
        # If file 3 of 5 fails, the first two are already on disk with no
        # DB rows pointing at them. Remove them before propagating.
        for item in results:
            remove_media_file(item["file_path"])
        raise
    return results