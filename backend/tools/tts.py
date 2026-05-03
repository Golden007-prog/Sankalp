"""Gemini / Cloud TTS narration for StoryAgent.

Maps Sankalp's 7-language launch set to plausible voice presets.
Returns a signed URL when STORAGE_BUCKET is set; degrades gracefully.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from tools._envelope import err, ok

log = logging.getLogger(__name__)

_VOICE_BY_LANG: dict[str, str] = {
    "en": "en-IN-Wavenet-D",
    "hi": "hi-IN-Wavenet-A",
    "bn": "bn-IN-Wavenet-A",
    "ta": "ta-IN-Wavenet-A",
    "kn": "kn-IN-Wavenet-A",
    "te": "te-IN-Standard-A",
    "mr": "mr-IN-Wavenet-A",
}


def tts_narrate(
    text: str, language: str = "en", voice: Optional[str] = None, session_id: Optional[str] = None,
) -> dict:
    if not text or not text.strip():
        return err("empty_text", "Nothing to narrate.")
    bucket = os.environ.get("STORAGE_BUCKET")
    voice_name = voice or _VOICE_BY_LANG.get(language, _VOICE_BY_LANG["en"])
    if not bucket:
        return ok(degraded=True, audio_url=None, voice=voice_name, language=language,
                  note="STORAGE_BUCKET not set; audio not persisted.")
    try:
        from google.cloud import texttospeech  # noqa: WPS433
        from google.cloud import storage  # noqa: WPS433
    except Exception as e:
        return ok(degraded=True, audio_url=None, voice=voice_name, language=language,
                  note=f"tts_sdk_unavailable: {e}")
    try:
        client = texttospeech.TextToSpeechClient()
        resp = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code=voice_name.rsplit("-", 1)[0] if "-" in voice_name else f"{language}-IN",
                name=voice_name,
            ),
            audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3),
        )
        audio = resp.audio_content
        sid = session_id or "anonymous"
        gcs = storage.Client()
        blob = gcs.bucket(bucket).blob(f"sessions/{sid}/narration.mp3")
        blob.upload_from_string(audio, content_type="audio/mpeg")
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        url = blob.generate_signed_url(version="v4", expiration=expires, method="GET")
        return ok(degraded=False, audio_url=url, voice=voice_name, language=language)
    except Exception as e:
        log.exception("tts call failed")
        return err(f"tts: {e}", "I couldn't generate the narration — text story still ready.")
