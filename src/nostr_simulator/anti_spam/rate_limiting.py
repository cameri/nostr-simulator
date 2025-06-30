"""Rate limiting anti-spam strategies."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float

    def consume(self, tokens: int = 1, current_time: float | None = None) -> bool:
        """Consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.
            current_time: Current time for refill calculation.

        Returns:
            True if tokens were consumed, False if insufficient tokens.
        """
        if current_time is None:
            current_time = time.time()

        # Refill tokens based on time elapsed
        elapsed = current_time - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = current_time

        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class TokenBucketRateLimiting(AntiSpamStrategy):
    """Token bucket rate limiting strategy."""

    def __init__(
        self,
        bucket_capacity: int = 10,
        refill_rate: float = 1.0,  # tokens per second
        tokens_per_event: int = 1,
    ) -> None:
        """Initialize token bucket rate limiting.

        Args:
            bucket_capacity: Maximum tokens in bucket.
            refill_rate: Rate at which tokens are added (per second).
            tokens_per_event: Tokens consumed per event.
        """
        super().__init__("token_bucket_rate_limiting")
        self.bucket_capacity = bucket_capacity
        self.refill_rate = refill_rate
        self.tokens_per_event = tokens_per_event
        self._buckets: dict[str, TokenBucket] = {}

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using token bucket rate limiting."""
        start_time = time.time()

        # Get or create bucket for this pubkey
        if event.pubkey not in self._buckets:
            self._buckets[event.pubkey] = TokenBucket(
                capacity=self.bucket_capacity,
                tokens=self.bucket_capacity,  # Start with full bucket
                refill_rate=self.refill_rate,
                last_refill=current_time,
            )

        bucket = self._buckets[event.pubkey]

        # Try to consume tokens
        if bucket.consume(self.tokens_per_event, current_time):
            allowed = True
            reason = "Token bucket allows event"
        else:
            allowed = False
            reason = f"Token bucket depleted (has {bucket.tokens:.1f}, needs {self.tokens_per_event})"

        computational_cost = time.time() - start_time

        metrics = {
            "remaining_tokens": bucket.tokens,
            "bucket_capacity": self.bucket_capacity,
            "refill_rate": self.refill_rate,
        }

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics=metrics,
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # State is updated in evaluate_event
        pass

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        total_buckets = len(self._buckets)
        total_tokens = sum(bucket.tokens for bucket in self._buckets.values())
        avg_tokens = total_tokens / total_buckets if total_buckets > 0 else 0

        return {
            "total_buckets": total_buckets,
            "average_tokens": avg_tokens,
            "bucket_capacity": self.bucket_capacity,
            "refill_rate": self.refill_rate,
        }


class SlidingWindowRateLimiting(AntiSpamStrategy):
    """Sliding window rate limiting strategy."""

    def __init__(
        self,
        window_size: float = 60.0,  # seconds
        max_events: int = 10,
        cleanup_interval: float = 300.0,  # Clean old entries every 5 minutes
    ) -> None:
        """Initialize sliding window rate limiting.

        Args:
            window_size: Size of the sliding window in seconds.
            max_events: Maximum events allowed in the window.
            cleanup_interval: How often to clean up old entries.
        """
        super().__init__("sliding_window_rate_limiting")
        self.window_size = window_size
        self.max_events = max_events
        self.cleanup_interval = cleanup_interval
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = 0.0

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using sliding window rate limiting."""
        start_time = time.time()

        # Periodic cleanup of old entries
        if current_time - self._last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time

        # Get window for this pubkey
        window = self._windows[event.pubkey]

        # Remove entries outside the window
        cutoff_time = current_time - self.window_size
        while window and window[0] <= cutoff_time:
            window.popleft()

        # Check if we're under the limit
        if len(window) < self.max_events:
            window.append(current_time)
            allowed = True
            reason = f"Within sliding window limit ({len(window)}/{self.max_events})"
        else:
            allowed = False
            reason = f"Sliding window limit exceeded ({len(window)}/{self.max_events})"

        computational_cost = time.time() - start_time

        metrics = {
            "events_in_window": len(window),
            "max_events": self.max_events,
            "window_size": self.window_size,
        }

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics=metrics,
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # State is updated in evaluate_event
        pass

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old entries from all windows."""
        cutoff_time = current_time - self.window_size * 2  # Keep some buffer

        for pubkey in list(self._windows.keys()):
            window = self._windows[pubkey]
            while window and window[0] <= cutoff_time:
                window.popleft()

            # Remove empty windows
            if not window:
                del self._windows[pubkey]

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        total_windows = len(self._windows)
        total_events = sum(len(window) for window in self._windows.values())
        avg_events = total_events / total_windows if total_windows > 0 else 0

        return {
            "total_windows": total_windows,
            "total_events_tracked": total_events,
            "average_events_per_window": avg_events,
            "window_size": self.window_size,
            "max_events": self.max_events,
        }


class AdaptiveRateLimiting(AntiSpamStrategy):
    """Adaptive rate limiting that adjusts based on observed behavior."""

    def __init__(
        self,
        base_limit: int = 10,
        window_size: float = 60.0,
        adaptation_factor: float = 0.5,
        min_limit: int = 1,
        max_limit: int = 100,
        adaptation_interval: float = 300.0,  # 5 minutes
    ) -> None:
        """Initialize adaptive rate limiting.

        Args:
            base_limit: Base rate limit.
            window_size: Window size for rate limiting.
            adaptation_factor: How much to adjust limits (0.0-1.0).
            min_limit: Minimum allowed limit.
            max_limit: Maximum allowed limit.
            adaptation_interval: How often to adapt limits.
        """
        super().__init__("adaptive_rate_limiting")
        self.base_limit = base_limit
        self.window_size = window_size
        self.adaptation_factor = adaptation_factor
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.adaptation_interval = adaptation_interval

        self._current_limits: dict[str, int] = defaultdict(lambda: base_limit)
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._spam_indicators: dict[str, int] = defaultdict(
            int
        )  # Count of suspicious behavior
        self._last_adaptation = 0.0

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using adaptive rate limiting."""
        start_time = time.time()

        # Periodic adaptation
        if current_time - self._last_adaptation > self.adaptation_interval:
            self._adapt_limits(current_time)
            self._last_adaptation = current_time

        # Get current limit and window for this pubkey
        current_limit = self._current_limits[event.pubkey]
        window = self._windows[event.pubkey]

        # Remove entries outside the window
        cutoff_time = current_time - self.window_size
        while window and window[0] <= cutoff_time:
            window.popleft()

        # Check if we're under the limit
        if len(window) < current_limit:
            window.append(current_time)
            allowed = True
            reason = f"Within adaptive limit ({len(window)}/{current_limit})"
        else:
            allowed = False
            reason = f"Adaptive limit exceeded ({len(window)}/{current_limit})"
            # Mark as potential spam
            self._spam_indicators[event.pubkey] += 1

        computational_cost = time.time() - start_time

        metrics = {
            "events_in_window": len(window),
            "current_limit": current_limit,
            "base_limit": self.base_limit,
            "spam_indicators": self._spam_indicators[event.pubkey],
        }

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics=metrics,
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # State is updated in evaluate_event
        pass

    def _adapt_limits(self, current_time: float) -> None:
        """Adapt rate limits based on observed behavior."""
        for pubkey in list(self._current_limits.keys()):
            spam_count = self._spam_indicators[pubkey]
            current_limit = self._current_limits[pubkey]

            if spam_count > 0:
                # Reduce limit for users with spam indicators
                adjustment = int(
                    current_limit * self.adaptation_factor * spam_count / 10
                )
                new_limit = max(self.min_limit, current_limit - adjustment)
            else:
                # Gradually increase limit for well-behaved users
                adjustment = int(self.base_limit * self.adaptation_factor / 10)
                new_limit = min(self.max_limit, current_limit + adjustment)

            self._current_limits[pubkey] = new_limit

            # Decay spam indicators
            self._spam_indicators[pubkey] = max(0, spam_count - 1)

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        if not self._current_limits:
            return {
                "total_tracked_users": 0,
                "average_limit": self.base_limit,
                "min_active_limit": self.base_limit,
                "max_active_limit": self.base_limit,
            }

        limits = list(self._current_limits.values())
        total_spam_indicators = sum(self._spam_indicators.values())

        return {
            "total_tracked_users": len(self._current_limits),
            "average_limit": sum(limits) / len(limits),
            "min_active_limit": min(limits),
            "max_active_limit": max(limits),
            "total_spam_indicators": total_spam_indicators,
            "base_limit": self.base_limit,
        }


class PerKeyRateLimiting(AntiSpamStrategy):
    """Per-key rate limiting with individual limits per public key."""

    def __init__(
        self,
        default_limit: int = 10,
        window_size: float = 60.0,
        custom_limits: dict[str, int] | None = None,
    ) -> None:
        """Initialize per-key rate limiting.

        Args:
            default_limit: Default rate limit for unknown keys.
            window_size: Window size for rate limiting.
            custom_limits: Custom limits for specific public keys.
        """
        super().__init__("per_key_rate_limiting")
        self.default_limit = default_limit
        self.window_size = window_size
        self.custom_limits = custom_limits or {}
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using per-key rate limiting."""
        start_time = time.time()

        # Get limit for this pubkey
        limit = self.custom_limits.get(event.pubkey, self.default_limit)
        window = self._windows[event.pubkey]

        # Remove entries outside the window
        cutoff_time = current_time - self.window_size
        while window and window[0] <= cutoff_time:
            window.popleft()

        # Check if we're under the limit
        if len(window) < limit:
            window.append(current_time)
            allowed = True
            reason = f"Within per-key limit ({len(window)}/{limit})"
        else:
            allowed = False
            reason = f"Per-key limit exceeded ({len(window)}/{limit})"

        computational_cost = time.time() - start_time

        metrics = {
            "events_in_window": len(window),
            "limit": limit,
            "is_custom_limit": event.pubkey in self.custom_limits,
        }

        return StrategyResult(
            allowed=allowed,
            reason=reason,
            metrics=metrics,
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # State is updated in evaluate_event
        pass

    def set_custom_limit(self, pubkey: str, limit: int) -> None:
        """Set a custom limit for a specific public key."""
        self.custom_limits[pubkey] = limit

    def remove_custom_limit(self, pubkey: str) -> None:
        """Remove custom limit for a public key."""
        self.custom_limits.pop(pubkey, None)

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        total_windows = len(self._windows)
        total_events = sum(len(window) for window in self._windows.values())
        custom_limit_users = len(self.custom_limits)

        return {
            "total_tracked_users": total_windows,
            "total_events_tracked": total_events,
            "custom_limit_users": custom_limit_users,
            "default_limit": self.default_limit,
            "window_size": self.window_size,
        }


class TrustedUserBypassRateLimiting(AntiSpamStrategy):
    """Rate limiting with bypass for trusted users."""

    def __init__(
        self,
        base_strategy: AntiSpamStrategy,
        trusted_pubkeys: set[str] | None = None,
        trust_threshold: float = 0.8,
        wot_strategy: AntiSpamStrategy | None = None,
    ) -> None:
        """Initialize trusted user bypass rate limiting.

        Args:
            base_strategy: Base rate limiting strategy to use.
            trusted_pubkeys: Set of explicitly trusted public keys.
            trust_threshold: WoT trust threshold for bypassing rate limits.
            wot_strategy: Web of Trust strategy for trust calculation.
        """
        super().__init__("trusted_user_bypass_rate_limiting")
        self.base_strategy = base_strategy
        self.trusted_pubkeys = trusted_pubkeys or set()
        self.trust_threshold = trust_threshold
        self.wot_strategy = wot_strategy

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event with trusted user bypass."""
        start_time = time.time()

        # Check if user is explicitly trusted
        if event.pubkey in self.trusted_pubkeys:
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=True,
                reason="Trusted user bypasses rate limiting",
                metrics={"bypass_reason": "explicit_trust"},
                computational_cost=computational_cost,
            )

        # Check WoT trust if available
        if self.wot_strategy:
            wot_result = self.wot_strategy.evaluate_event(event, current_time)
            if (
                wot_result.metrics
                and wot_result.metrics.get("trust_score", 0) >= self.trust_threshold
            ):
                computational_cost = time.time() - start_time
                return StrategyResult(
                    allowed=True,
                    reason=f"WoT trusted user bypasses rate limiting (trust={wot_result.metrics['trust_score']:.2f})",
                    metrics={
                        "bypass_reason": "wot_trust",
                        "trust_score": wot_result.metrics["trust_score"],
                    },
                    computational_cost=computational_cost,
                )

        # Apply base rate limiting strategy
        base_result = self.base_strategy.evaluate_event(event, current_time)

        computational_cost = time.time() - start_time

        return StrategyResult(
            allowed=base_result.allowed,
            reason=f"Base rate limiting: {base_result.reason}",
            metrics={
                "base_metrics": base_result.metrics,
                "bypass_reason": None,
            },
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event."""
        # Update base strategy state if event was not bypassed
        if event.pubkey not in self.trusted_pubkeys:
            if (
                not self.wot_strategy
                or self._get_trust_score(event, current_time) < self.trust_threshold
            ):
                self.base_strategy.update_state(event, current_time)

        # Update WoT strategy state if available
        if self.wot_strategy:
            self.wot_strategy.update_state(event, current_time)

    def _get_trust_score(self, event: NostrEvent, current_time: float) -> float:
        """Get trust score from WoT strategy."""
        if not self.wot_strategy:
            return 0.0

        result = self.wot_strategy.evaluate_event(event, current_time)
        return result.metrics.get("trust_score", 0.0) if result.metrics else 0.0

    def add_trusted_pubkey(self, pubkey: str) -> None:
        """Add a public key to the trusted set."""
        self.trusted_pubkeys.add(pubkey)

    def remove_trusted_pubkey(self, pubkey: str) -> None:
        """Remove a public key from the trusted set."""
        self.trusted_pubkeys.discard(pubkey)

    def get_metrics(self) -> dict[str, Any]:
        """Get strategy metrics."""
        base_metrics = self.base_strategy.get_metrics()
        wot_metrics = self.wot_strategy.get_metrics() if self.wot_strategy else {}

        return {
            "trusted_pubkeys_count": len(self.trusted_pubkeys),
            "trust_threshold": self.trust_threshold,
            "base_strategy_metrics": base_metrics,
            "wot_strategy_metrics": wot_metrics,
        }
