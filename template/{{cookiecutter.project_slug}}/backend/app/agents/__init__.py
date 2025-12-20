{%- if cookiecutter.enable_ai_agent %}
"""AI Agents module using PydanticAI.

This module contains agents that handle AI-powered interactions.
Tools are defined in the tools/ subdirectory.
"""

from app.agents.assistant import AssistantAgent, Deps

__all__ = ["AssistantAgent", "Deps"]
{%- else %}
"""AI Agents - not configured."""
{%- endif %}
