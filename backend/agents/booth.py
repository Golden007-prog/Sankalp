"""BoothAgent — polling-booth lookup, directions, accessibility.

Verbatim prompt from docs/AGENTS.md §4.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.common import MODEL_FLASH, flash_config, load_prompt
from tools.epic_search import (
    get_accessibility,
    lookup_booth_by_epic,
    lookup_booth_by_pin,
)
from tools.maps import get_directions, nearest_landmarks


def build() -> LlmAgent:
    return LlmAgent(
        name="booth_agent",
        description="Finds the user's polling booth and provides directions + accessibility info.",
        model=MODEL_FLASH,
        instruction=load_prompt("booth"),
        generate_content_config=flash_config(temperature=0.2, max_output_tokens=1024),
        tools=[
            FunctionTool(lookup_booth_by_epic),
            FunctionTool(lookup_booth_by_pin),
            FunctionTool(get_accessibility),
            FunctionTool(get_directions),
            FunctionTool(nearest_landmarks),
        ],
    )


booth_agent = build()
