"""OrchestratorAgent — the front door.

Verbatim prompt from docs/AGENTS.md §1. Detects language, routes intent
to one of four AgentTool-wrapped specialists, and persists session state.
Specialists never call siblings — only their own domain tools — so this
file is the single re-entry point per ARCHITECTURE.md §3.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from agents.booth import booth_agent
from agents.common import MODEL_FLASH, flash_config, load_prompt
from agents.registration import registration_agent
from agents.story import story_agent
from agents.verification import verification_agent
from tools.language import detect_language
from tools.session import load_session, update_session


def build() -> LlmAgent:
    return LlmAgent(
        name="orchestrator",
        description="Sankalp's root agent. Detects language, classifies intent, routes to a specialist.",
        model=MODEL_FLASH,
        instruction=load_prompt("orchestrator"),
        generate_content_config=flash_config(),
        tools=[
            FunctionTool(detect_language),
            FunctionTool(load_session),
            FunctionTool(update_session),
            AgentTool(agent=registration_agent),
            AgentTool(agent=verification_agent),
            AgentTool(agent=booth_agent),
            AgentTool(agent=story_agent),
        ],
    )


orchestrator = build()
