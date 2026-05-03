"""VerificationAgent — EPIC search + duplicate detection.

Verbatim prompt from docs/AGENTS.md §3.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.common import MODEL_FLASH, flash_config, load_prompt
from tools.epic_search import dedup_check, epic_search, parse_epic_ocr, suggest_corrections


def build() -> LlmAgent:
    return LlmAgent(
        name="verification_agent",
        description="Looks up voter records by EPIC or name+DOB and surfaces duplicates / corrections.",
        model=MODEL_FLASH,
        instruction=load_prompt("verification"),
        generate_content_config=flash_config(),
        tools=[
            FunctionTool(epic_search),
            FunctionTool(dedup_check),
            FunctionTool(suggest_corrections),
            FunctionTool(parse_epic_ocr),
        ],
    )


verification_agent = build()
