"""Form 6 and Form 8 PDF generation.

We do NOT bundle the official ECI gazetted forms (license + size). Instead
we emit a clean Sankalp lookalike with the same field labels, order, and
section structure as ECI Form 6 and Form 8. The PDF footer carries the
trust-boundary disclosure: the user submits the official form themselves
on voters.eci.gov.in. See docs/ARCHITECTURE.md §6.1 + AGENTS.md §2.

Phase-2 scope: Helvetica only (English-language form; bilingual rendering
deferred until NotoSans Devanagari is bundled in a later phase). The
form_state may carry full_name_native — we still render English labels but
print the user's native-script name where given.

Cloud Storage upload + signed URL when STORAGE_BUCKET is set, otherwise a
local file under backend/data/_pdfs/ with a file:// URL — keeps hermetic
tests free.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from tools._envelope import err, ok

log = logging.getLogger(__name__)

LOCAL_PDF_DIR = Path(__file__).resolve().parents[1] / "data" / "_pdfs"
LOCAL_PDF_DIR.mkdir(parents=True, exist_ok=True)

DISCLAIMER_LINE_1 = "Sankalp-generated approximation of ECI Form {n}."
DISCLAIMER_LINE_2 = "Submit the official form at voters.eci.gov.in."


def generate_form6_pdf(session_id: str, form_state: dict) -> dict:
    return _generate(session_id, form_state, form_n="6", change_type=None)


def generate_form8_pdf(session_id: str, form_state: dict, change_type: str) -> dict:
    if change_type not in ("address", "name", "photo", "all"):
        return err("invalid_change_type", "change_type must be one of: address, name, photo, all.")
    return _generate(session_id, form_state, form_n="8", change_type=change_type)


def _generate(session_id: str, form_state: dict, form_n: str, change_type: Optional[str]) -> dict:
    if not session_id or len(session_id) < 8:
        return err("invalid_session_id", "Internal: missing session id.")
    try:
        pdf_bytes = _render_pdf(form_state, form_n=form_n, change_type=change_type)
    except Exception as e:
        log.exception("PDF render failed")
        return err(f"render_failed: {e}", "I had trouble generating your PDF — please try again.")

    filename = f"form{form_n}_{session_id}.pdf"
    bucket = os.environ.get("STORAGE_BUCKET")
    if bucket:
        try:
            url = _upload_to_gcs(bucket, session_id, filename, pdf_bytes)
            return ok(url=url, form_type=form_n, filename=filename, storage="cloud")
        except Exception as e:
            log.warning("GCS upload failed (%s); writing locally", e)

    out_path = LOCAL_PDF_DIR / filename
    out_path.write_bytes(pdf_bytes)
    return ok(
        url=out_path.as_uri(),
        form_type=form_n,
        filename=filename,
        storage="local",
        size_bytes=len(pdf_bytes),
    )


def _upload_to_gcs(bucket: str, session_id: str, filename: str, payload: bytes) -> str:
    from google.cloud import storage  # noqa: WPS433

    client = storage.Client()
    blob = client.bucket(bucket).blob(f"sessions/{session_id}/{filename}")
    blob.upload_from_string(payload, content_type="application/pdf")
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    return blob.generate_signed_url(version="v4", expiration=expires, method="GET")


def _render_pdf(form_state: dict[str, Any], form_n: str, change_type: Optional[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    margin = 18 * mm
    y = page_h - margin

    # Header.
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, f"FORM {form_n}")
    c.setFont("Helvetica", 9)
    c.drawRightString(page_w - margin, y + 2, "(see Rule 13(1) of the Registration of Electors Rules, 1960)")
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 12)
    if form_n == "6":
        title = "Application for inclusion of name in electoral roll"
    else:
        title = f"Application for correction in electoral roll — {change_type or 'all'}"
    c.drawString(margin, y, title)
    y -= 6 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        margin, y,
        DISCLAIMER_LINE_1.format(n=form_n) + "  " + DISCLAIMER_LINE_2,
    )
    y -= 8 * mm

    # Section 1 — applicant.
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "1. Applicant details"); y -= 6 * mm
    c.setFont("Helvetica", 10)
    y = _kv(c, margin, y, "Full name", form_state.get("full_name", ""))
    if form_state.get("full_name_native"):
        # reportlab Helvetica can't render Devanagari etc. — print the
        # native string verbatim and let the PDF reader handle missing
        # glyphs. Most viewers degrade gracefully to .notdef boxes; the
        # English label is the legal field anyway.
        y = _kv(c, margin, y, "Name (native script)", form_state.get("full_name_native", ""))
    y = _kv(c, margin, y, "Date of birth", form_state.get("dob", ""))
    y = _kv(c, margin, y, "Gender", _gender_label(form_state.get("gender")))
    y = _kv(
        c, margin, y, "Relation",
        f"{form_state.get('relation_type', '')}: {form_state.get('relation_name', '')}",
    )
    if form_state.get("epic_number"):
        y = _kv(c, margin, y, "Existing EPIC", form_state["epic_number"])

    # Section 2 — address.
    y -= 3 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "2. Address"); y -= 6 * mm
    c.setFont("Helvetica", 10)
    y = _kv(c, margin, y, "House", form_state.get("house", ""))
    y = _kv(c, margin, y, "Street", form_state.get("street", ""))
    y = _kv(c, margin, y, "Locality", form_state.get("locality", ""))
    y = _kv(c, margin, y, "City", form_state.get("city", ""))
    y = _kv(c, margin, y, "State", form_state.get("state", ""))
    y = _kv(c, margin, y, "Pincode", form_state.get("pincode", ""))

    # Section 3 — contact (optional).
    if form_state.get("mobile") or form_state.get("email"):
        y -= 3 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, "3. Contact (optional)"); y -= 6 * mm
        c.setFont("Helvetica", 10)
        if form_state.get("mobile"):
            y = _kv(c, margin, y, "Mobile", form_state["mobile"])
        if form_state.get("email"):
            y = _kv(c, margin, y, "Email", form_state["email"])

    # Section 4 — assembly constituency.
    y -= 3 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "4. Assembly Constituency"); y -= 6 * mm
    c.setFont("Helvetica", 10)
    y = _kv(c, margin, y, "AC code", form_state.get("ac_code", ""))
    y = _kv(c, margin, y, "AC name", form_state.get("ac_name", ""))

    # Declaration block.
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Declaration"); y -= 6 * mm
    c.setFont("Helvetica", 9)
    decl = (
        "I declare that to the best of my knowledge and belief I am a citizen of India and "
        "the particulars given above are true. I understand that submitting this application "
        "is the User's responsibility — Sankalp does not submit on the User's behalf."
    )
    y = _wrap_text(c, decl, margin, y, page_w - 2 * margin, 9)

    # Footer.
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(margin, 12 * mm, DISCLAIMER_LINE_1.format(n=form_n))
    c.drawString(margin, 8 * mm, DISCLAIMER_LINE_2)
    c.drawRightString(
        page_w - margin, 8 * mm,
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    )

    c.showPage()
    c.save()
    return buf.getvalue()


def _kv(c: canvas.Canvas, x: float, y: float, label: str, value: str) -> float:
    c.drawString(x, y, f"{label}:")
    c.drawString(x + 45 * mm, y, value or "—")
    c.line(x + 45 * mm, y - 0.5 * mm, x + 180 * mm, y - 0.5 * mm)
    return y - 6 * mm


def _gender_label(g: Optional[str]) -> str:
    return {"M": "Male", "F": "Female", "T": "Third Gender"}.get(g or "", "")


def _wrap_text(c: canvas.Canvas, text: str, x: float, y: float, max_w: float, font_sz: float) -> float:
    words = text.split()
    line: list[str] = []
    line_h = font_sz + 2
    for w in words:
        trial = " ".join(line + [w])
        if c.stringWidth(trial, "Helvetica", font_sz) > max_w:
            c.drawString(x, y, " ".join(line))
            y -= line_h
            line = [w]
        else:
            line.append(w)
    if line:
        c.drawString(x, y, " ".join(line))
        y -= line_h
    return y
