"""Anti-spam strategies for Nostr simulator."""

from .base import AntiSpamStrategy, StrategyResult
from .hashchain import HashchainRollingCodes, TimeBasedCodeRotation
from .pow import ProofOfWorkStrategy
from .rate_limiting import (
    AdaptiveRateLimiting,
    PerKeyRateLimiting,
    SlidingWindowRateLimiting,
    TokenBucketRateLimiting,
    TrustedUserBypassRateLimiting,
)
from .reputation_tokens import ReputationTokenRenewal, ReputationTokenStrategy
from .wot import WebOfTrustStrategy

__all__ = [
    "AntiSpamStrategy",
    "StrategyResult",
    "ProofOfWorkStrategy",
    "WebOfTrustStrategy",
    "TokenBucketRateLimiting",
    "SlidingWindowRateLimiting",
    "AdaptiveRateLimiting",
    "PerKeyRateLimiting",
    "TrustedUserBypassRateLimiting",
    "HashchainRollingCodes",
    "TimeBasedCodeRotation",
    "ReputationTokenStrategy",
    "ReputationTokenRenewal",
]
