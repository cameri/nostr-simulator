"""Tests for rate limiting anti-spam strategies."""

import time
from unittest.mock import Mock

from ..protocol.events import NostrEvent, NostrEventKind
from .rate_limiting import (
    AdaptiveRateLimiting,
    PerKeyRateLimiting,
    SlidingWindowRateLimiting,
    TokenBucket,
    TokenBucketRateLimiting,
    TrustedUserBypassRateLimiting,
)


class TestTokenBucket:
    """Test TokenBucket functionality."""

    def test_token_bucket_creation(self) -> None:
        """Test token bucket creation."""
        bucket = TokenBucket(
            capacity=10,
            tokens=10.0,
            refill_rate=1.0,
            last_refill=0.0,
        )

        assert bucket.capacity == 10
        assert bucket.tokens == 10.0
        assert bucket.refill_rate == 1.0
        assert bucket.last_refill == 0.0

    def test_token_consumption(self) -> None:
        """Test token consumption."""
        bucket = TokenBucket(
            capacity=10,
            tokens=5.0,
            refill_rate=1.0,
            last_refill=0.0,
        )

        # Should be able to consume available tokens
        assert bucket.consume(3, 0.0) is True
        assert bucket.tokens == 2.0

        # Should not be able to consume more than available
        assert bucket.consume(5, 0.0) is False
        assert bucket.tokens == 2.0

    def test_token_refill(self) -> None:
        """Test token refill over time."""
        bucket = TokenBucket(
            capacity=10,
            tokens=0.0,
            refill_rate=2.0,  # 2 tokens per second
            last_refill=0.0,
        )

        # After 3 seconds, should have 6 tokens
        assert bucket.consume(1, 3.0) is True
        assert bucket.tokens == 5.0  # 6 - 1 consumed
        # last_refill is now 3.0

        # After another 2 seconds (5 total), should be 5 + (2*2) = 9, consume 1 = 8
        assert bucket.consume(1, 5.0) is True
        assert bucket.tokens == 8.0  # Was 5, added 4 (2*2), consumed 1

    def test_token_refill_cap(self) -> None:
        """Test token refill is capped at capacity."""
        bucket = TokenBucket(
            capacity=5,
            tokens=0.0,
            refill_rate=10.0,  # Very high refill rate
            last_refill=0.0,
        )

        # After 10 seconds, should be capped at capacity
        bucket.consume(0, 10.0)  # Just trigger refill
        assert bucket.tokens == 5.0


class TestTokenBucketRateLimiting:
    """Test TokenBucketRateLimiting strategy."""

    def create_test_event(self, pubkey: str = "test_pubkey") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=[],
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        strategy = TokenBucketRateLimiting(
            bucket_capacity=5,
            refill_rate=1.0,
            tokens_per_event=1,
        )

        assert strategy.name == "token_bucket_rate_limiting"
        assert strategy.bucket_capacity == 5
        assert strategy.refill_rate == 1.0
        assert strategy.tokens_per_event == 1

    def test_initial_events_allowed(self) -> None:
        """Test that initial events are allowed (full bucket)."""
        strategy = TokenBucketRateLimiting(bucket_capacity=3, refill_rate=1.0)
        event = self.create_test_event()

        # First 3 events should be allowed
        for i in range(3):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True
            assert "allows" in result.reason

        # 4th event should be blocked
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False
        assert "depleted" in result.reason

    def test_token_refill_allows_more_events(self) -> None:
        """Test that token refill allows more events."""
        strategy = TokenBucketRateLimiting(bucket_capacity=2, refill_rate=1.0)
        event = self.create_test_event()

        # Consume all tokens
        strategy.evaluate_event(event, 0.0)
        strategy.evaluate_event(event, 0.0)

        # Should be blocked immediately
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

        # After 2 seconds, should have 2 tokens again
        result = strategy.evaluate_event(event, 2.0)
        assert result.allowed is True

    def test_different_pubkeys_separate_buckets(self) -> None:
        """Test that different pubkeys have separate buckets."""
        strategy = TokenBucketRateLimiting(bucket_capacity=1, refill_rate=1.0)

        event1 = self.create_test_event("pubkey1")
        event2 = self.create_test_event("pubkey2")

        # Both should be allowed (separate buckets)
        result1 = strategy.evaluate_event(event1, 0.0)
        result2 = strategy.evaluate_event(event2, 0.0)

        assert result1.allowed is True
        assert result2.allowed is True

        # Both should be blocked for second events
        result1 = strategy.evaluate_event(event1, 0.0)
        result2 = strategy.evaluate_event(event2, 0.0)

        assert result1.allowed is False
        assert result2.allowed is False

    def test_metrics(self) -> None:
        """Test strategy metrics."""
        strategy = TokenBucketRateLimiting(bucket_capacity=5, refill_rate=2.0)
        event = self.create_test_event()

        # Process some events
        strategy.evaluate_event(event, 0.0)
        strategy.evaluate_event(event, 0.0)

        result = strategy.evaluate_event(event, 1.0)  # Allow refill

        assert result.metrics is not None
        assert "remaining_tokens" in result.metrics
        assert "bucket_capacity" in result.metrics
        assert result.metrics["bucket_capacity"] == 5
        assert result.metrics["refill_rate"] == 2.0


class TestSlidingWindowRateLimiting:
    """Test SlidingWindowRateLimiting strategy."""

    def create_test_event(self, pubkey: str = "test_pubkey") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=[],
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        strategy = SlidingWindowRateLimiting(
            window_size=30.0,
            max_events=5,
        )

        assert strategy.name == "sliding_window_rate_limiting"
        assert strategy.window_size == 30.0
        assert strategy.max_events == 5

    def test_events_within_limit_allowed(self) -> None:
        """Test that events within limit are allowed."""
        strategy = SlidingWindowRateLimiting(window_size=60.0, max_events=3)
        event = self.create_test_event()

        # First 3 events should be allowed
        for i in range(3):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True
            assert f"({i+1}/3)" in result.reason

        # 4th event should be blocked
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False
        assert "(3/3)" in result.reason

    def test_sliding_window_expiry(self) -> None:
        """Test that old events expire from the window."""
        strategy = SlidingWindowRateLimiting(window_size=30.0, max_events=2)
        event = self.create_test_event()

        # Fill the window
        strategy.evaluate_event(event, 0.0)
        strategy.evaluate_event(event, 10.0)

        # Should be blocked
        result = strategy.evaluate_event(event, 20.0)
        assert result.allowed is False

        # After window expires, should be allowed
        result = strategy.evaluate_event(event, 40.0)  # First event expired
        assert result.allowed is True

    def test_different_pubkeys_separate_windows(self) -> None:
        """Test that different pubkeys have separate windows."""
        strategy = SlidingWindowRateLimiting(window_size=60.0, max_events=1)

        event1 = self.create_test_event("pubkey1")
        event2 = self.create_test_event("pubkey2")

        # Both should be allowed (separate windows)
        result1 = strategy.evaluate_event(event1, 0.0)
        result2 = strategy.evaluate_event(event2, 0.0)

        assert result1.allowed is True
        assert result2.allowed is True

    def test_cleanup_old_entries(self) -> None:
        """Test cleanup of old entries."""
        strategy = SlidingWindowRateLimiting(
            window_size=60.0,
            max_events=10,
            cleanup_interval=100.0,
        )

        # Create events for multiple pubkeys
        for i in range(5):
            event = self.create_test_event(f"pubkey{i}")
            strategy.evaluate_event(event, 0.0)

        assert len(strategy._windows) == 5

        # Trigger cleanup by advancing time
        dummy_event = self.create_test_event("dummy")
        strategy.evaluate_event(dummy_event, 200.0)

        # Old entries should be cleaned up
        # Only the dummy event should remain
        assert len(strategy._windows) == 1


class TestAdaptiveRateLimiting:
    """Test AdaptiveRateLimiting strategy."""

    def create_test_event(self, pubkey: str = "test_pubkey") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=[],
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        strategy = AdaptiveRateLimiting(
            base_limit=10,
            adaptation_factor=0.5,
            min_limit=2,
            max_limit=50,
        )

        assert strategy.name == "adaptive_rate_limiting"
        assert strategy.base_limit == 10
        assert strategy.adaptation_factor == 0.5
        assert strategy.min_limit == 2
        assert strategy.max_limit == 50

    def test_initial_limit_is_base_limit(self) -> None:
        """Test that initial limit is the base limit."""
        strategy = AdaptiveRateLimiting(base_limit=5)
        event = self.create_test_event()

        # Should allow base_limit events
        for i in range(5):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True

        # Should block the next one
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

    def test_limit_decreases_for_spam(self) -> None:
        """Test that limit decreases for users who hit limits."""
        strategy = AdaptiveRateLimiting(
            base_limit=5,
            adaptation_factor=0.5,
            adaptation_interval=10.0,
        )
        event = self.create_test_event()

        # Hit the limit multiple times
        for _ in range(10):
            strategy.evaluate_event(
                event, 0.0
            )  # This will hit limit and increase spam indicators

        # Trigger adaptation
        strategy.evaluate_event(event, 15.0)

        # Limit should be reduced
        assert strategy._current_limits[event.pubkey] < strategy.base_limit

    def test_limit_increases_for_good_behavior(self) -> None:
        """Test that limit gradually increases for well-behaved users."""
        strategy = AdaptiveRateLimiting(
            base_limit=5,
            adaptation_factor=0.5,
            adaptation_interval=10.0,
        )
        event = self.create_test_event()

        # Use the service normally (under limit)
        for i in range(3):
            strategy.evaluate_event(event, float(i))

        # Trigger adaptation without hitting limits
        strategy.evaluate_event(event, 15.0)

        # Limit should increase or stay at base
        assert strategy._current_limits[event.pubkey] >= strategy.base_limit

    def test_limits_respect_bounds(self) -> None:
        """Test that limits respect min/max bounds."""
        strategy = AdaptiveRateLimiting(
            base_limit=5,
            min_limit=2,
            max_limit=8,
            adaptation_factor=1.0,  # High factor for quick changes
            adaptation_interval=1.0,
        )
        event = self.create_test_event()

        # Simulate lots of spam to hit min limit
        for _ in range(20):
            for _ in range(10):
                strategy.evaluate_event(event, 0.0)
            strategy._adapt_limits(1.0)  # Force adaptation

        assert strategy._current_limits[event.pubkey] >= strategy.min_limit

        # Reset and test max limit
        strategy._spam_indicators[event.pubkey] = 0
        strategy._current_limits[event.pubkey] = strategy.base_limit

        # Simulate good behavior to hit max limit
        for _ in range(20):
            strategy._adapt_limits(1.0)

        assert strategy._current_limits[event.pubkey] <= strategy.max_limit


class TestPerKeyRateLimiting:
    """Test PerKeyRateLimiting strategy."""

    def create_test_event(self, pubkey: str = "test_pubkey") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=[],
            content="test content",
            sig="test_sig",
        )

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        custom_limits = {"special_key": 20}
        strategy = PerKeyRateLimiting(
            default_limit=10,
            window_size=60.0,
            custom_limits=custom_limits,
        )

        assert strategy.name == "per_key_rate_limiting"
        assert strategy.default_limit == 10
        assert strategy.window_size == 60.0
        assert strategy.custom_limits == custom_limits

    def test_default_limit_applied(self) -> None:
        """Test that default limit is applied to unknown keys."""
        strategy = PerKeyRateLimiting(default_limit=3)
        event = self.create_test_event("unknown_key")

        # Should allow default_limit events
        for i in range(3):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True
            assert result.metrics is not None
            assert result.metrics["limit"] == 3
            assert result.metrics["is_custom_limit"] is False

        # Should block the next one
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

    def test_custom_limit_applied(self) -> None:
        """Test that custom limit is applied to specific keys."""
        custom_limits = {"special_key": 5}
        strategy = PerKeyRateLimiting(
            default_limit=2,
            custom_limits=custom_limits,
        )
        event = self.create_test_event("special_key")

        # Should allow custom limit events (5, not 2)
        for i in range(5):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True
            assert result.metrics is not None
            assert result.metrics["limit"] == 5
            assert result.metrics["is_custom_limit"] is True

        # Should block the next one
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

    def test_set_custom_limit(self) -> None:
        """Test setting custom limits dynamically."""
        strategy = PerKeyRateLimiting(default_limit=2)

        # Initially uses default limit
        event = self.create_test_event("test_key")
        for _ in range(2):
            result = strategy.evaluate_event(event, 0.0)
            assert result.allowed is True

        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

        # Set custom limit and reset window
        strategy.set_custom_limit("test_key", 5)

        # Should now allow more events
        result = strategy.evaluate_event(event, 70.0)  # Reset window
        assert result.allowed is True
        assert result.metrics is not None
        assert result.metrics["limit"] == 5

    def test_remove_custom_limit(self) -> None:
        """Test removing custom limits."""
        custom_limits = {"test_key": 10}
        strategy = PerKeyRateLimiting(
            default_limit=2,
            custom_limits=custom_limits,
        )

        # Initially uses custom limit
        event = self.create_test_event("test_key")
        result = strategy.evaluate_event(event, 0.0)
        assert result.metrics is not None
        assert result.metrics["limit"] == 10

        # Remove custom limit
        strategy.remove_custom_limit("test_key")

        # Should now use default limit
        result = strategy.evaluate_event(event, 70.0)  # Reset window
        assert result.metrics is not None
        assert result.metrics["limit"] == 2


class TestTrustedUserBypassRateLimiting:
    """Test TrustedUserBypassRateLimiting strategy."""

    def create_test_event(self, pubkey: str = "test_pubkey") -> NostrEvent:
        """Create a test event."""
        return NostrEvent(
            id="test_id",
            pubkey=pubkey,
            created_at=int(time.time()),
            kind=NostrEventKind.TEXT_NOTE,
            tags=[],
            content="test content",
            sig="test_sig",
        )

    def create_mock_wot_strategy(self, trust_score: float) -> Mock:
        """Create a mock WoT strategy."""
        mock_strategy = Mock()
        mock_result = Mock()
        mock_result.metrics = {"trust_score": trust_score}
        mock_strategy.evaluate_event.return_value = mock_result
        return mock_strategy

    def test_strategy_creation(self) -> None:
        """Test strategy creation."""
        base_strategy = TokenBucketRateLimiting()
        trusted_pubkeys = {"trusted_key"}

        strategy = TrustedUserBypassRateLimiting(
            base_strategy=base_strategy,
            trusted_pubkeys=trusted_pubkeys,
            trust_threshold=0.8,
        )

        assert strategy.name == "trusted_user_bypass_rate_limiting"
        assert strategy.base_strategy == base_strategy
        assert strategy.trusted_pubkeys == trusted_pubkeys
        assert strategy.trust_threshold == 0.8

    def test_explicit_trusted_user_bypass(self) -> None:
        """Test that explicitly trusted users bypass rate limiting."""
        base_strategy = TokenBucketRateLimiting(bucket_capacity=1)  # Very restrictive
        trusted_pubkeys = {"trusted_key"}

        strategy = TrustedUserBypassRateLimiting(
            base_strategy=base_strategy,
            trusted_pubkeys=trusted_pubkeys,
        )

        trusted_event = self.create_test_event("trusted_key")
        untrusted_event = self.create_test_event("untrusted_key")

        # Trusted user should always be allowed
        for _ in range(10):  # Way more than base strategy would allow
            result = strategy.evaluate_event(trusted_event, 0.0)
            assert result.allowed is True
            assert "Trusted user bypasses" in result.reason
            assert result.metrics is not None
            assert result.metrics["bypass_reason"] == "explicit_trust"

        # Untrusted user should be limited by base strategy
        result = strategy.evaluate_event(untrusted_event, 0.0)
        assert result.allowed is True  # First event allowed

        result = strategy.evaluate_event(untrusted_event, 0.0)
        assert result.allowed is False  # Second event blocked by token bucket

    def test_wot_trusted_user_bypass(self) -> None:
        """Test that WoT trusted users bypass rate limiting."""
        base_strategy = TokenBucketRateLimiting(bucket_capacity=1)
        wot_strategy = self.create_mock_wot_strategy(0.9)  # High trust

        strategy = TrustedUserBypassRateLimiting(
            base_strategy=base_strategy,
            wot_strategy=wot_strategy,
            trust_threshold=0.8,
        )

        event = self.create_test_event("wot_trusted_key")

        # Should bypass rate limiting due to high WoT trust
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is True
        assert "WoT trusted user bypasses" in result.reason
        assert result.metrics is not None
        assert result.metrics["bypass_reason"] == "wot_trust"
        assert result.metrics["trust_score"] == 0.9

    def test_low_wot_trust_uses_base_strategy(self) -> None:
        """Test that low WoT trust users use base strategy."""
        base_strategy = TokenBucketRateLimiting(bucket_capacity=1)
        wot_strategy = self.create_mock_wot_strategy(0.3)  # Low trust

        strategy = TrustedUserBypassRateLimiting(
            base_strategy=base_strategy,
            wot_strategy=wot_strategy,
            trust_threshold=0.8,
        )

        event = self.create_test_event("low_trust_key")

        # First event should be allowed by base strategy
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is True
        assert "Base rate limiting" in result.reason

        # Second event should be blocked by base strategy
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False
        assert "Base rate limiting" in result.reason

    def test_add_remove_trusted_pubkey(self) -> None:
        """Test adding and removing trusted pubkeys."""
        base_strategy = TokenBucketRateLimiting(bucket_capacity=1)
        strategy = TrustedUserBypassRateLimiting(base_strategy=base_strategy)

        event = self.create_test_event("test_key")

        # Initially not trusted
        strategy.evaluate_event(event, 0.0)  # Use up the token
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is False

        # Add to trusted set
        strategy.add_trusted_pubkey("test_key")
        result = strategy.evaluate_event(event, 0.0)
        assert result.allowed is True
        assert "Trusted user bypasses" in result.reason

        # Remove from trusted set
        strategy.remove_trusted_pubkey("test_key")
        result = strategy.evaluate_event(event, 10.0)  # Allow token refill
        strategy.evaluate_event(event, 10.0)  # Use up token
        result = strategy.evaluate_event(event, 10.0)
        assert result.allowed is False

    def test_update_state_propagation(self) -> None:
        """Test that update_state is properly propagated."""
        base_strategy = Mock()
        wot_strategy = Mock()
        wot_strategy.evaluate_event.return_value.metrics = {"trust_score": 0.3}

        strategy = TrustedUserBypassRateLimiting(
            base_strategy=base_strategy,
            wot_strategy=wot_strategy,
            trust_threshold=0.8,
        )

        event = self.create_test_event("test_key")

        # Update state for non-trusted user
        strategy.update_state(event, 0.0)

        # Both strategies should be updated
        base_strategy.update_state.assert_called_once_with(event, 0.0)
        wot_strategy.update_state.assert_called_once_with(event, 0.0)

        # Reset mocks
        base_strategy.reset_mock()
        wot_strategy.reset_mock()

        # Update state for trusted user
        strategy.add_trusted_pubkey("test_key")
        strategy.update_state(event, 0.0)

        # Only WoT strategy should be updated for trusted users
        base_strategy.update_state.assert_not_called()
        wot_strategy.update_state.assert_called_once_with(event, 0.0)
