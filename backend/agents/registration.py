"""RegistrationAgent — Form 6 (new voter) / Form 8 (corrections).

Verbatim prompt from docs/AGENTS.md §2 (loaded from prompts/registration.md).
Owns slot-filling, validation, and PDF generation. Never submits to ECI.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agents.common import MODEL_FLASH, flash_config, load_prompt
from tools.constituency import pin_to_constituency, validate_field
from tools.form_pdf import generate_form6_pdf, generate_form8_pdf
from tools.session import update_session as update_session_tool


def update_form_state(session_id: str, delta: dict) -> dict:
    """Persist partial form-fill across turns. Wraps Orchestrator's session
    tool so the specialist's writes go through the same audit path."""
    return update_session_tool(session_id, {"form_state": delta})


def build() -> LlmAgent:
    return LlmAgent(
        name="registration_agent",
        description="Walks the user through Form 6 (new voter) or Form 8 (corrections) one field at a time.",
        model=MODEL_FLASH,
        instruction=load_prompt("registration"),
        generate_content_config=flash_config(),
        tools=[
            FunctionTool(validate_field),
            FunctionTool(pin_to_constituency),
            FunctionTool(generate_form6_pdf),
            FunctionTool(generate_form8_pdf),
            FunctionTool(update_form_state),
        ],
    )


registration_agent = build()
