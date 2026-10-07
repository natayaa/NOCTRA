"""Public inquiry form: GET the form, POST the submission."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.logging import log
from app.modules.inquiries.constants import (
    BUDGET_LABELS,
    BUDGET_RANGES,
    COLOR_FAMILIES,
    COLOR_LABELS,
    FINISH_LABELS,
    FINISH_TYPES,
    PREFERENCE_KEYS,
    SERVICE_INTEREST_LABELS,
    SERVICE_INTERESTS,
)
from app.modules.vehicles.constants import VEHICLE_CATEGORIES
from app.services.public_intake import PublicIntakePayload, PublicIntakeService
from app.web.templates_env import templates

router = APIRouter(tags=["public-contact"])


def _catalog_context() -> dict:
    return {
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "finishes": FINISH_TYPES,
        "finish_labels": FINISH_LABELS,
        "color_families": COLOR_FAMILIES,
        "color_labels": COLOR_LABELS,
        "budget_ranges": BUDGET_RANGES,
        "budget_labels": BUDGET_LABELS,
        "vehicle_categories": VEHICLE_CATEGORIES,
        "preference_keys": PREFERENCE_KEYS,
    }


@router.get("/contact", response_class=HTMLResponse)
async def contact_form(request: Request) -> HTMLResponse:
    return templates.render(
        request,
        "public/contact.html",
        {"title": "Contact NOCTRA", **_catalog_context()},
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
    form = await request.form()

    # ── Honeypot ─────────────────────────────────────
    if (form.get("website") or "").strip():
        return RedirectResponse(url="/contact/success", status_code=303)

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
                "title": "Contact NOCTRA",
                "error": exc.message,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=exc.status_code,
        )

    await db.commit()

    log.info(
        "contact_submit_committed",
        inquiry_id=str(inquiry.id),
        inquiry_code=inquiry.code,
        customer_id=str(inquiry.customer_id),
        vehicle_id=str(inquiry.vehicle_id) if inquiry.vehicle_id else None,
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