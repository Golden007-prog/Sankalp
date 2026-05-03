"""Shared helpers for the five ADK agents."""
from __future__ import annotations

import os
from pathlib import Path

from google.genai import types as genai_types

PROMPT_DIR = Path(__file__).parent / "prompts"

# Model strings — see CLAUDE.md "Stack". Flash for routing/specialists,
# Pro for the StoryAgent narrative moment.
MODEL_FLASH = os.environ.get("SANKALP_MODEL_FLASH", "gemini-2.5-flash")
MODEL_PRO = os.environ.get("SANKALP_MODEL_PRO", "gemini-2.5-pro")


def load_prompt(name: str) -> str:
    """Read the verbatim prompt from disk. The ADK substitutes
    {language_code} from session state at runtime — see ARCHITECTURE.md §5.
    """
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def flash_config(temperature: float = 0.2, max_output_tokens: int = 2048) -> genai_types.GenerateContentConfig:
    return genai_types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def pro_config(temperature: float = 0.7, max_output_tokens: int = 4096) -> genai_types.GenerateContentConfig:
    return genai_types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
