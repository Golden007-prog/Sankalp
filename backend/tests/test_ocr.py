"""OCR multi-strategy parser tests.

Hermetic cases use a fake Vision client that returns canned
`full_text_annotation.text`. Live cases (`pytest -m live`) run real
Cloud Vision against samples/epics/*.jpg and assert ≥4/5 accuracy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

from tools import ocr as ocr_mod
from tools.ocr import _parse_with_heuristics


# ---------- helpers for hermetic mocks ----------

@dataclass
class _Annotation:
    text: str = ""


@dataclass
class _Resp:
    full_text_annotation: Optional[_Annotation] = None
    error: object = field(default_factory=lambda: type("E", (), {"message": ""})())


class _FakeClient:
    def __init__(self, doc_text: str = "", text_text: Optional[str] = None) -> None:
        self._doc = doc_text
        self._text = text_text if text_text is not None else doc_text

    def document_text_detection(self, image):  # noqa: ARG002
        return _Resp(full_text_annotation=_Annotation(text=self._doc))

    def text_detection(self, image):  # noqa: ARG002
        return _Resp(full_text_annotation=_Annotation(text=self._text))


@pytest.fixture(autouse=True)
def _stub_vision(monkeypatch):
    """Replace `from google.cloud import vision` with a stub package
    that returns whatever the test wired up via `set_fake`."""
    state: dict[str, _FakeClient] = {}

    class _ImageWrapper:
        def __init__(self, content: bytes) -> None:
            self.content = content

    class _Pkg:
        @staticmethod
        def ImageAnnotatorClient():  # noqa: N802
            return state["client"]
        Image = _ImageWrapper  # noqa: N815

    import sys
    monkeypatch.setitem(sys.modules, "google.cloud.vision", _Pkg)

    def _set_fake(client: _FakeClient) -> None:
        state["client"] = client

    yield _set_fake


# ---------- helper-fn unit tests ----------

def test_parse_strict() -> None:
    epic, conf, alts = _parse_with_heuristics("Voter ID: ABC1234567 issued 2020")
    assert epic == "ABC1234567"
    assert conf == 0.85
    assert alts == []


def test_parse_with_whitespace_in_epic() -> None:
    epic, conf, _ = _parse_with_heuristics("EPIC No: ABC 1234567")
    assert epic == "ABC1234567"
    assert conf == 0.85


def test_parse_loose_with_substitution() -> None:
    """OCR misreads 2 as Z; loose pass + char-fix recovers it."""
    epic, conf, alts = _parse_with_heuristics("EPIC: ABC1Z34567 (faded)")
    assert epic == "ABC1234567"
    assert conf == 0.65
    assert "ABC1234567" in alts


def test_parse_no_match() -> None:
    epic, conf, _ = _parse_with_heuristics("This card is unreadable")
    assert epic is None
    assert conf == 0.0


# ---------- end-to-end hermetic via stubbed Vision client ----------

def test_e2e_clean_document_path(_stub_vision) -> None:
    _stub_vision(_FakeClient(doc_text="ELECTION COMMISSION OF INDIA\nEPIC No.\nABC1234567"))
    out = ocr_mod.detect_epic_text(b"\xff\xd8\xff fake jpeg")
    assert out["ok"] is True
    assert out["epic_number"] == "ABC1234567"
    assert out["strategy_used"] == "document_text_detection"
    # cross-check against MockElectoralDataSource boosts confidence + names Riya
    assert out["matched_name"] == "Riya Sharma"
    assert out["confidence"] >= 0.9


def test_e2e_falls_back_to_text_detection(_stub_vision) -> None:
    """DOCUMENT mode returns nothing usable; TEXT mode finds the EPIC."""
    _stub_vision(_FakeClient(doc_text="", text_text="EPIC ABC1234567"))
    out = ocr_mod.detect_epic_text(b"\xff\xd8\xff")
    assert out["ok"] is True
    assert out["epic_number"] == "ABC1234567"
    assert out["strategy_used"] == "text_detection_fallback"


def test_e2e_no_epic_anywhere(_stub_vision) -> None:
    _stub_vision(_FakeClient(doc_text="page is blank", text_text="page is blank"))
    out = ocr_mod.detect_epic_text(b"\xff\xd8\xff")
    assert out["ok"] is True
    assert out["epic_number"] is None
    assert out["confidence"] == 0.0
    assert out["strategy_used"] == "none"


def test_e2e_empty_image_returns_envelope_error() -> None:
    out = ocr_mod.detect_epic_text(b"")
    assert out["ok"] is False
    assert out["error"] == "empty_image"
    assert "user_message" in out


# ---------- live test against samples/epics/*.jpg ----------

@pytest.mark.live
def test_live_ocr_sample_epics_accuracy() -> None:
    """≥4/5 sample EPIC images parse to the correct number."""
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() != "true":
        pytest.skip("vertex env not configured")
    samples = Path(__file__).resolve().parents[2] / "samples" / "epics"
    if not samples.exists():
        pytest.skip("samples/epics/ not generated")

    expected = {
        "riya": "ABC1234567",
        "ravi": "BIH7821093",
        "priya": "TGS9912204",
        "dedup_a": "DUP1112223",
        "dedup_b": "DUP4445556",
    }

    # Bypass the autouse Vision stub by importing the real module fresh.
    import importlib
    import sys
    sys.modules.pop("google.cloud.vision", None)
    real_ocr = importlib.reload(ocr_mod)

    correct = 0
    for stem, expected_epic in expected.items():
        path = samples / f"{stem}.jpg"
        if not path.exists():
            continue
        out = real_ocr.detect_epic_text(path.read_bytes())
        if out.get("epic_number") == expected_epic:
            correct += 1
        print(
            f"  {stem:10s} -> {out.get('epic_number')!s:12s} "
            f"conf={out.get('confidence')} strategy={out.get('strategy_used')}"
        )
    assert correct >= 4, f"only {correct}/5 sample EPICs parsed correctly"
