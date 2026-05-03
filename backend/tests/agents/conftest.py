"""Shared fixtures for agent tests."""
from __future__ import annotations

import pytest

from agents.booth import booth_agent
from agents.orchestrator import orchestrator
from agents.registration import registration_agent
from agents.story import story_agent
from agents.verification import verification_agent


@pytest.fixture(scope="session")
def all_agents() -> dict:
    return {
        "orchestrator": orchestrator,
        "registration": registration_agent,
        "verification": verification_agent,
        "booth": booth_agent,
        "story": story_agent,
    }


def tool_names(agent) -> set[str]:
    return {t.name for t in agent.tools}
