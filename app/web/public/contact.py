"""Public inquiry form: GET the form, POST the submission."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.core.csrf import get_form
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.form_guard import check_form_timestamp, make_form_timestamp
from app.core.logging import log
from app.core.rate_limit import RateLimitMiddleware, limiter
from app.modules.inquiries.constants import (
    BUDGET_LABELS,
    BUDGET_RANGES,
    COLOR_FAMILIES,
    COLOR_LABELS,
    FINISH_LABELS,
    FINISH_TYPES,
    PREFERENCE_KEYS,
    SERVICE_INTERESTS,
)
from app.modules.settings.constants import (
    KEY_PUBLIC_INQUIRY_ENABLED,
    KEY_PUBLIC_INQUIRY_RATE_LIMIT,
    KEY_PUBLIC_PHONE,
)
from app.modules.settings.service import SettingsService
from app.modules.vehicles.constants import VEHICLE_CATEGORIES
from app.services.public_intake import PublicIntakePayload, PublicIntakeService
from app.web.templates_env import templates

router = APIRouter(tags=["public-contact"])

# Admin-facing labels stay English; the public form uses Indonesian.
PUBLIC_SERVICE_LABELS: dict[str, str] = {
    "REPAINT": "Full Body Repaint",
    "PANEL_REPAINT": "Panel Repaint",
    "RESTORATION": "Restorasi",
    "CUSTOM_PAINT": "Custom Paint",
    "DETAILING": "Detailing & Poles",
    "PANEL_REPAIR": "Perbaikan Panel",
    "OTHER": "Lainnya / belum yakin",
}

PUBLIC_PREFERENCE_LABELS: dict[str, str] = {
    "keep_decals": "Pertahankan decal asli",
    "pinstripe": "Pinstriping",
    "chrome_work": "Area krom yang perlu dipoles",
    "preferred_brand_clearcoat": "Merek clear coat pilihan",
    "matching_oem_color": "Warna OEM yang ingin disamakan",
    "reference_photo_url": "URL foto referensi",
    "custom_notes": "Permintaan khusus lainnya",
}


def _catalog_context() -> dict:
    return {
        "services": SERVICE_INTERESTS,
        "service_labels": PUBLIC_SERVICE_LABELS,
        "finishes": FINISH_TYPES,
        "finish_labels": FINISH_LABELS,
        "color_families": COLOR_FAMILIES,
        "color_labels": COLOR_LABELS,
        "budget_ranges": BUDGET_RANGES,
        "budget_labels": BUDGET_LABELS,
        "vehicle_categories": VEHICLE_CATEGORIES,
        "preference_keys": [
            {**pk, "label": PUBLIC_PREFERENCE_LABELS.get(pk["key"], pk["label"])}
            for pk in PREFERENCE_KEYS
        ],
    }


def _as_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() not in {"false", "0", "no", "off"}


async def _inquiries_enabled(db) -> bool:
    raw = await SettingsService(db).get_value(KEY_PUBLIC_INQUIRY_ENABLED, "true")
    return _as_bool(raw, default=True)


@router.get("/contact", response_class=HTMLResponse)
async def contact_form(request: Request, db: DbSession) -> HTMLResponse:
    if not await _inquiries_enabled(db):
        phone = await SettingsService(db).get_value(
            KEY_PUBLIC_PHONE, settings.PUBLIC_PHONE
        )
        return templates.render(
            request,
            "public/contact_closed.html",
            {
                "title": "Kontak — NOCTRA",
                "public_phone": phone,
                **_catalog_context(),
            },
            status_code=503,
        )

    requested = (request.query_params.get("service") or "").strip().upper()
    form_values = {"service_interest": requested} if requested in SERVICE_INTERESTS else {}
    return templates.render(
        request,
        "public/contact.html",
        {
            "title": "Kontak — NOCTRA",
            "form_values": form_values,
            "form_timestamp": make_form_timestamp(),
            **_catalog_context(),
        },
    )


@router.get("/contact/success", response_class=HTMLResponse)
async def contact_success(request: Request) -> HTMLResponse:
    ref = request.query_params.get("ref", "")
    return templates.render(
        request,
        "public/inquiry_success.html",
        {"title": "Thank you", "reference": ref},
    )


@router.post("/contact")
async def contact_submit(request: Request, db: DbSession):
    form = await get_form(request)

    # ── Honeypot ─────────────────────────────────────
    if (form.get("website") or "").strip():
        await form.close()
        return RedirectResponse(url="/contact/success", status_code=303)

    # ── Time trap (signed render timestamp) ─────────
    # Answered with the success page on purpose: a bot that learns it was
    # rejected will adapt, while a real user never sees this branch.
    time_ok, time_reason = check_form_timestamp(form.get("_form_ts"))
    if not time_ok:
        await form.close()
        log.warning(
            "contact_submit_form_guard_rejected",
            reason=time_reason,
            ip=RateLimitMiddleware._client_ip(request),
        )
        return RedirectResponse(url="/contact/success", status_code=303)

    # ── Acceptance toggle ────────────────────────────
    if not await _inquiries_enabled(db):
        await form.close()
        log.warning("contact_submit_disabled")
        phone = await SettingsService(db).get_value(
            KEY_PUBLIC_PHONE, settings.PUBLIC_PHONE
        )
        return templates.render(
            request,
            "public/contact_closed.html",
            {
                "title": "Kontak — NOCTRA",
                "public_phone": phone,
                **_catalog_context(),
            },
            status_code=503,
        )

    # ── Per-IP hourly cap (public.inquiry_rate_limit_per_hour) ──
    raw_limit = await SettingsService(db).get_value(
        KEY_PUBLIC_INQUIRY_RATE_LIMIT, None
    )
    try:
        per_hour = int(float(raw_limit)) if raw_limit not in (None, "") else 0
    except (TypeError, ValueError):
        per_hour = 0
    if per_hour > 0:
        ip = RateLimitMiddleware._client_ip(request)
        allowed, _retry_after = limiter.hit(f"inquiry:{ip}", per_hour, 3600)
        if not allowed:
            await form.close()
            log.warning("contact_submit_rate_limited", ip=ip)
            return templates.render(
                request,
                "public/contact.html",
                {
                    "title": "Kontak — NOCTRA",
                    "error": "Terlalu banyak permintaan dari alamat ini. "
                             "Silakan coba lagi nanti.",
                    "form_timestamp": make_form_timestamp(),
                    "form_values": dict(form),
                    **_catalog_context(),
                },
                status_code=429,
            )

    # ── Preferences from pref_* fields ───────────────
    preferences: dict = {}
    for pk in PREFERENCE_KEYS:
        raw = form.get(f"pref_{pk['key']}")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        if pk["type"] == "bool":
            preferences[pk["key"]] = raw == "true"
        elif pk["type"] == "list":
            preferences[pk["key"]] = [s.strip() for s in str(raw).split(",") if s.strip()]
        else:
            preferences[pk["key"]] = str(raw).strip()

    # ── Photos ───────────────────────────────────────
    photos: list[UploadFile] = []
    for key in ("photo_1", "photo_2", "photo_3", "photo_4", "photo_5"):
        f = form.get(key)
        if f is not None and hasattr(f, "filename") and f.filename:
            photos.append(f)

    # ── Payload ──────────────────────────────────────
    try:
        payload = PublicIntakePayload(
            name=(form.get("name") or "").strip(),
            phone=(form.get("phone") or "").strip(),
            email=(form.get("email") or "").strip() or None,
            vehicle_brand=(form.get("vehicle_brand") or "").strip() or None,
            vehicle_model=(form.get("vehicle_model") or "").strip() or None,
            vehicle_year=int(form["vehicle_year"]) if form.get("vehicle_year") else None,
            vehicle_plate=(form.get("vehicle_plate") or "").strip() or None,
            vehicle_category=(form.get("vehicle_category") or "").strip() or None,
            service_interest=(form.get("service_interest") or "").strip() or None,
            description=(form.get("description") or "").strip(),
            color_preference=(form.get("color_preference") or "").strip() or None,
            color_family=(form.get("color_family") or "").strip() or None,
            finish_preference=(form.get("finish_preference") or "").strip() or None,
            has_custom_graphics=form.get("has_custom_graphics") == "true",
            preferences=preferences or None,
            budget_range=(form.get("budget_range") or "").strip() or None,
            desired_date=(
                date.fromisoformat(form["desired_date"]) if form.get("desired_date") else None
            ),
        )
    except (TypeError, ValueError):
        # Malformed year / date used to escape as an unhandled 500 on a
        # public endpoint (and leaked the spooled upload files).
        await form.close()
        log.warning("contact_submit_invalid_payload")
        return templates.render(
            request,
            "public/contact.html",
            {
                "title": "Kontak — NOCTRA",
                "error": "Mohon periksa kembali tahun kendaraan dan tanggal yang dipilih.",
                "form_timestamp": make_form_timestamp(),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=400,
        )

    log.info(
        "contact_submit_received",
        name=payload.name,
        phone=payload.phone,
        vehicle_brand=payload.vehicle_brand,
        vehicle_model=payload.vehicle_model,
        photo_count=len(photos),
    )

    try:
        inquiry = await PublicIntakeService(db).submit(payload, photos=photos)
    except AppError as exc:
        await db.rollback()
        log.warning(
            "contact_submit_rejected",
            code=exc.code,
            message=exc.message,
            status=exc.status_code,
            photo_count=len(photos),
        )
        return templates.render(
            request,
            "public/contact.html",
            {
                "title": "Kontak — NOCTRA",
                "error": exc.message,
                "form_timestamp": make_form_timestamp(),
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=exc.status_code,
        )
    finally:
        # FormData owns Starlette's spooled upload files; close them on
        # both the success and validation-error paths.
        await form.close()

    await db.commit()

    log.info(
        "contact_submit_committed",
        inquiry_id=str(inquiry.id),
        inquiry_code=inquiry.code,
        customer_id=str(inquiry.customer_id),
        vehicle_id=str(inquiry.vehicle_id) if inquiry.vehicle_id else None,
    )

    # A double-click / retry lands on the existing inquiry. Show the same
    # reference, but do not email the shop and customer twice.
    if getattr(inquiry, "_deduplicated", False):
        log.info(
            "contact_submit_deduplicated",
            inquiry_id=str(inquiry.id),
            inquiry_code=inquiry.code,
        )
        return RedirectResponse(
            url=f"/contact/success?ref={inquiry.code}", status_code=303
        )

    # ── Notifications (fire-and-forget) ──────────────
    # Capture plain values BEFORE the request ends.
    notify_payload = {
        "inquiry_id": inquiry.id,
        "inquiry_code": inquiry.code,
        "service_interest": inquiry.service_interest,
        "description": inquiry.description,
        "color_family": inquiry.color_family,
        "color_preference": inquiry.color_preference,
        "finish_preference": inquiry.finish_preference,
        "has_custom_graphics": inquiry.has_custom_graphics,
        "budget_range": inquiry.budget_range,
        "desired_date": inquiry.desired_date,
        **getattr(inquiry, "_notify_context", {}),
    }

    from app.core.jobs import queue

    async def _dispatch():
        from app.core.database import SessionLocal
        from app.services.notifications import notify_inquiry_received

        async with SessionLocal() as session:
            try:
                await notify_inquiry_received(session, **notify_payload)
                await session.commit()
            except Exception:
                await session.rollback()
                log.exception("notification_dispatch_failed", code=notify_payload.get("inquiry_code"))

    await queue.enqueue(_dispatch)

    return RedirectResponse(url=f"/contact/success?ref={inquiry.code}", status_code=303)