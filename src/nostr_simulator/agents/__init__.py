"""Agent framework for the Nostr simulator."""

from .adversarial import SybilAttackerAgent
from .base import AgentState, AgentType, BaseAgent, Message
from .client import ClientAgent
from .relay import RelayAgent
from .user import HonestUserAgent, UserBehaviorPattern

__all__ = [
    # Base classes
    "AgentState",
    "AgentType",
    "BaseAgent",
    "Message",
    # User agents
    "HonestUserAgent",
    "UserBehaviorPattern",
    # Network agents
    "ClientAgent",
    "RelayAgent",
    # Adversarial agents
    "SybilAttackerAgent",
]
