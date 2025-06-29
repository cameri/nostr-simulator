"""Tests for Proof of Work anti-spam strategy."""

from unittest.mock import Mock, patch

import pytest

from nostr_simulator.anti_spam.pow import ProofOfWorkStrategy
from nostr_simulator.protocol.events import NostrEvent


class TestProofOfWorkStrategy:
    """Test ProofOfWorkStrategy class."""

    def test_pow_strategy_initialization(self) -> None:
        """Test PoW strategy initialization."""
        strategy = ProofOfWorkStrategy(
            min_difficulty=4,
            max_difficulty=16,
            target_solve_time=10.0,
            adjustment_period=100,
            adaptive=True,
        )

        assert strategy.name == "proof_of_work"
        assert strategy.min_difficulty == 4
        assert strategy.max_difficulty == 16
        assert strategy.target_solve_time == 10.0
        assert strategy.adjustment_period == 100
        assert strategy.adaptive is True
        assert strategy.current_difficulty == 4

    def test_pow_strategy_default_initialization(self) -> None:
        """Test PoW strategy with default values."""
        strategy = ProofOfWorkStrategy()

        assert strategy.min_difficulty == 8
        assert strategy.max_difficulty == 24
        assert strategy.target_solve_time == 5.0
        assert strategy.adjustment_period == 2016  # Bitcoin-style
        assert strategy.adaptive is True
        assert strategy.current_difficulty == 8

    def test_calculate_pow_difficulty_zero_difficulty(self) -> None:
        """Test calculating PoW difficulty for an event with no leading zeros."""
        strategy = ProofOfWorkStrategy()

        # Create a mock event with an ID that has no leading zeros
        event = Mock(spec=NostrEvent)
        event.id = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

        difficulty = strategy._calculate_pow_difficulty(event)
        assert difficulty == 0

    def test_calculate_pow_difficulty_with_leading_zeros(self) -> None:
        """Test calculating PoW difficulty for an event with leading zeros."""
        strategy = ProofOfWorkStrategy()

        # Create a mock event with an ID that has 8 leading zero bits (2 hex zeros)
        event = Mock(spec=NostrEvent)
        event.id = "00abcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        difficulty = strategy._calculate_pow_difficulty(event)
        assert difficulty == 8  # 2 hex zeros = 8 bits

    def test_calculate_pow_difficulty_partial_hex_zeros(self) -> None:
        """Test calculating PoW difficulty with partial hex digit zeros."""
        strategy = ProofOfWorkStrategy()

        # Create an event with leading zeros in binary but not full hex zeros
        event = Mock(spec=NostrEvent)
        event.id = "08bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        difficulty = strategy._calculate_pow_difficulty(event)
        # 0x08 = 0b1000, so we have 4 leading zero bits
        assert difficulty == 4

    def test_evaluate_event_insufficient_pow(self) -> None:
        """Test evaluating an event with insufficient PoW."""
        strategy = ProofOfWorkStrategy(min_difficulty=8)

        # Create an event with only 4 bits of PoW
        event = Mock(spec=NostrEvent)
        event.id = "08bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is False
        assert "Insufficient PoW" in result.reason
        assert result.computational_cost == 0.0  # No computation needed for validation

    def test_evaluate_event_sufficient_pow(self) -> None:
        """Test evaluating an event with sufficient PoW."""
        strategy = ProofOfWorkStrategy(min_difficulty=4)

        # Create an event with 8 bits of PoW (exceeds minimum of 4)
        event = Mock(spec=NostrEvent)
        event.id = "00bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        result = strategy.evaluate_event(event, 1000.0)

        assert result.allowed is True
        assert "PoW valid" in result.reason
        assert result.computational_cost == 0.0  # Validation cost

    def test_update_state_tracks_metrics(self) -> None:
        """Test that update_state tracks metrics correctly."""
        strategy = ProofOfWorkStrategy()

        event = Mock(spec=NostrEvent)
        event.id = "00bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        # Initially no metrics
        assert strategy.get_metrics()["events_processed"] == 0

        strategy.update_state(event, 1000.0)

        metrics = strategy.get_metrics()
        assert metrics["events_processed"] == 1
        assert metrics["total_difficulty"] == 8
        assert metrics["avg_difficulty"] == 8.0

    def test_difficulty_adjustment_increase(self) -> None:
        """Test difficulty adjustment when solve time is too fast."""
        strategy = ProofOfWorkStrategy(
            min_difficulty=4,
            max_difficulty=16,
            target_solve_time=10.0,
            adjustment_period=2,
            adaptive=True,
        )

        # Simulate events being processed faster than target
        event = Mock(spec=NostrEvent)
        event.id = "00bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        # Process first event
        strategy.update_state(event, 1000.0)

        # Process second event quickly (2 seconds later, vs target of 10 seconds)
        strategy.update_state(event, 1002.0)

        # Should trigger difficulty adjustment
        assert strategy.current_difficulty > 4

    def test_difficulty_adjustment_decrease(self) -> None:
        """Test difficulty adjustment when solve time is too slow."""
        strategy = ProofOfWorkStrategy(
            min_difficulty=4,
            max_difficulty=16,
            target_solve_time=5.0,
            adjustment_period=2,
            adaptive=True,
        )

        # Start with higher difficulty
        strategy.current_difficulty = 12

        # Simulate events being processed slower than target
        event = Mock(spec=NostrEvent)
        event.id = "00bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        # Process first event
        strategy.update_state(event, 1000.0)

        # Process second event slowly (20 seconds later, vs target of 5 seconds)
        strategy.update_state(event, 1020.0)

        # Should trigger difficulty adjustment downward
        assert strategy.current_difficulty < 12

    def test_difficulty_adjustment_bounds(self) -> None:
        """Test that difficulty adjustment respects min/max bounds."""
        strategy = ProofOfWorkStrategy(
            min_difficulty=4,
            max_difficulty=8,
            target_solve_time=10.0,
            adjustment_period=2,
            adaptive=True,
        )

        # Try to adjust beyond maximum
        strategy.current_difficulty = 8
        strategy._adjust_difficulty(1.0)  # Very fast solve time
        assert strategy.current_difficulty == 8  # Should not exceed max

        # Try to adjust below minimum
        strategy.current_difficulty = 4
        strategy._adjust_difficulty(100.0)  # Very slow solve time
        assert strategy.current_difficulty == 4  # Should not go below min

    def test_adaptive_disabled(self) -> None:
        """Test that difficulty adjustment is disabled when adaptive=False."""
        strategy = ProofOfWorkStrategy(adaptive=False)
        original_difficulty = strategy.current_difficulty

        event = Mock(spec=NostrEvent)
        event.id = "00bcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

        # Process many events quickly
        for i in range(10):
            strategy.update_state(event, 1000.0 + i)

        # Difficulty should not change
        assert strategy.current_difficulty == original_difficulty

    def test_mine_nonce_for_difficulty(self) -> None:
        """Test mining a nonce to achieve target difficulty."""
        strategy = ProofOfWorkStrategy()

        # Create base event data
        event_data = {
            "pubkey": "test_pubkey",
            "created_at": 1234567890,
            "kind": 1,
            "tags": [],
            "content": "test content",
        }

        target_difficulty = 4

        # Mock the mining process to avoid actual computation
        with patch.object(strategy, "_calculate_pow_difficulty_from_id") as mock_calc:
            # Set up mock to return insufficient difficulty first, then sufficient
            mock_calc.side_effect = [2, 3, 6]  # Third attempt succeeds

            # Mock time.time() to return consistent values for timing calculation
            time_values = [1000.0] + [
                1000.0 + i * 0.01 for i in range(1, 10)
            ]  # Enough calls
            with patch("time.time", side_effect=time_values):
                nonce, actual_difficulty, solve_time = (
                    strategy.mine_nonce_for_difficulty(event_data, target_difficulty)
                )

        assert isinstance(nonce, int)
        assert nonce == 2  # Should have tried nonces 0, 1, 2
        assert actual_difficulty == 6  # From our mock
        assert solve_time > 0.0  # Should have some solve time

    def test_mine_nonce_timeout(self) -> None:
        """Test mining with timeout."""
        strategy = ProofOfWorkStrategy()

        event_data = {
            "pubkey": "test_pubkey",
            "created_at": 1234567890,
            "kind": 1,
            "tags": [],
            "content": "test content",
        }

        # Mock the difficulty calculation to always return insufficient difficulty
        with patch.object(
            strategy, "_calculate_pow_difficulty_from_id", return_value=0
        ):
            # Mock time to simulate timeout - start time + multiple loop iterations + final timeout check
            time_values = (
                [1000.0] + [1000.0 + i * 0.1 for i in range(1, 20)] + [1002.0]
            )  # Exceeds 1s timeout
            with patch("time.time", side_effect=time_values):
                with pytest.raises(TimeoutError):
                    strategy.mine_nonce_for_difficulty(
                        event_data,
                        target_difficulty=20,
                        timeout=1.0,
                        max_attempts=10000,
                    )

    def test_mine_nonce_max_attempts(self) -> None:
        """Test mining with max attempts limit."""
        strategy = ProofOfWorkStrategy()

        event_data = {
            "pubkey": "test_pubkey",
            "created_at": 1234567890,
            "kind": 1,
            "tags": [],
            "content": "test content",
        }

        # Mock the difficulty calculation to always return insufficient difficulty
        with patch.object(
            strategy, "_calculate_pow_difficulty_from_id", return_value=0
        ):
            with pytest.raises(
                ValueError, match="Failed to find nonce.*within.*attempts"
            ):
                strategy.mine_nonce_for_difficulty(
                    event_data, target_difficulty=20, timeout=100.0, max_attempts=10
                )

    def test_metrics_collection(self) -> None:
        """Test comprehensive metrics collection."""
        strategy = ProofOfWorkStrategy()

        # Process events with different difficulties
        events = [
            Mock(spec=NostrEvent, id="00bcdef1234567890" + "0" * 47),  # 8 bits
            Mock(spec=NostrEvent, id="000cdef1234567890" + "0" * 47),  # 12 bits
            Mock(spec=NostrEvent, id="0000def1234567890" + "0" * 47),  # 16 bits
        ]

        for i, event in enumerate(events):
            strategy.update_state(event, 1000.0 + i * 10)

        metrics = strategy.get_metrics()
        assert metrics["events_processed"] == 3
        assert metrics["total_difficulty"] == 36  # 8 + 12 + 16
        assert metrics["avg_difficulty"] == 12.0
        assert metrics["current_difficulty"] == strategy.current_difficulty
