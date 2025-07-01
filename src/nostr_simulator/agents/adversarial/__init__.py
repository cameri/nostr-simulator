"""Adversarial agents for simulating attacks on Nostr."""

from .burst_spammer import BurstSpammerAgent
from .hash_link_spammer import HashLinkSpammerAgent
from .replay_attacker import ReplayAttackerAgent
from .sybil_attacker import SybilAttackerAgent

__all__ = [
    "BurstSpammerAgent",
    "HashLinkSpammerAgent",
    "ReplayAttackerAgent",
    "SybilAttackerAgent",
]
