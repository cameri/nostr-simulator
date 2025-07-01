"""Adversarial agents for simulating attacks on Nostr."""

from .burst_spammer import BurstSpammerAgent
from .sybil_attacker import SybilAttackerAgent

__all__ = [
    "BurstSpammerAgent",
    "SybilAttackerAgent",
]
