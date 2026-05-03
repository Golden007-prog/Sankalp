"""StoryAgent — personalised civic narrative. The demo moment.

Verbatim prompt from docs/AGENTS.md §5. Uses Gemini 2.5 Pro because
narrative quality matters here (see CLAUDE.md "Stack" rule 4).
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.common import MODEL_PRO, load_prompt, pro_config
from tools.constituency import (
    get_constituency,
    get_turnout_history,
    get_win_margin_history,
)
from tools.imagen import imagen_cover
from tools.story_store import store_story
from tools.tts import tts_narrate


def build() -> LlmAgent:
    return LlmAgent(
        name="story_agent",
        description="Writes a 200-word personalised civic narrative for the user's constituency.",
        model=MODEL_PRO,
        instruction=load_prompt("story"),
        generate_content_config=pro_config(),
        tools=[
            FunctionTool(get_constituency),
            FunctionTool(get_turnout_history),
            FunctionTool(get_win_margin_history),
            FunctionTool(imagen_cover),
            FunctionTool(tts_narrate),
            FunctionTool(store_story),
        ],
    )


story_agent = build()
