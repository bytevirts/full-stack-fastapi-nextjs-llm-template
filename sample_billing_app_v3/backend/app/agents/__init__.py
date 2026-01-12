"""AI Agents module using CrewAI.

This module contains a multi-agent crew built with CrewAI.
Agents work together in a team to accomplish complex tasks.
"""

from app.agents.crewai_assistant import CrewAIAssistant, CrewConfig, CrewContext

__all__ = ["CrewAIAssistant", "CrewConfig", "CrewContext"]
