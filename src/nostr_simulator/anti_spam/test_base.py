"""Tests for base anti-spam strategy classes."""

from unittest.mock import Mock

import pytest

from nostr_simulator.anti_spam.base import AntiSpamStrategy, StrategyResult
from nostr_simulator.protocol.events import NostrEvent


class TestStrategyResult:
    """Test StrategyResult dataclass."""

    def test_strategy_result_creation(self) -> None:
        """Test creating a StrategyResult."""
        result = StrategyResult(
            allowed=True,
            reason="Valid event",
            metrics={"processed": 1},
            computational_cost=0.1,
        )

        assert result.allowed is True
        assert result.reason == "Valid event"
        assert result.metrics == {"processed": 1}
        assert result.computational_cost == 0.1

    def test_strategy_result_defaults(self) -> None:
        """Test StrategyResult with default values."""
        result = StrategyResult(allowed=False, reason="Blocked")

        assert result.allowed is False
        assert result.reason == "Blocked"
        assert result.metrics is None
        assert result.computational_cost == 0.0


class MockStrategy(AntiSpamStrategy):
    """Mock strategy for testing."""

    def __init__(self, name: str = "mock") -> None:
        super().__init__(name)
        self.evaluate_calls: list[tuple[NostrEvent, float]] = []
        self.update_calls: list[tuple[NostrEvent, float]] = []

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Mock evaluation that always allows."""
        self.evaluate_calls.append((event, current_time))
        return StrategyResult(allowed=True, reason="Mock strategy allows all")

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Mock state update."""
        self.update_calls.append((event, current_time))


class TestAntiSpamStrategy:
    """Test AntiSpamStrategy abstract base class."""

    def test_strategy_initialization(self) -> None:
        """Test strategy initialization."""
        strategy = MockStrategy("test_strategy")

        assert strategy.name == "test_strategy"
        assert strategy.get_metrics() == {}

    def test_strategy_metrics(self) -> None:
        """Test metrics management."""
        strategy = MockStrategy()

        # Initially empty
        assert strategy.get_metrics() == {}

        # Add some metrics
        strategy._metrics["events_processed"] = 5
        strategy._metrics["blocks"] = 2

        metrics = strategy.get_metrics()
        assert metrics == {"events_processed": 5, "blocks": 2}

        # Ensure we get a copy, not the original
        metrics["new_key"] = "should not affect original"
        assert "new_key" not in strategy.get_metrics()

    def test_strategy_reset_metrics(self) -> None:
        """Test resetting metrics."""
        strategy = MockStrategy()

        strategy._metrics["test"] = 123
        assert strategy.get_metrics() == {"test": 123}

        strategy.reset_metrics()
        assert strategy.get_metrics() == {}

    def test_mock_strategy_evaluate_event(self) -> None:
        """Test mock strategy evaluation."""
        strategy = MockStrategy()
        event = Mock(spec=NostrEvent)
        current_time = 1234.5

        result = strategy.evaluate_event(event, current_time)

        assert result.allowed is True
        assert result.reason == "Mock strategy allows all"
        assert len(strategy.evaluate_calls) == 1
        assert strategy.evaluate_calls[0] == (event, current_time)

    def test_mock_strategy_update_state(self) -> None:
        """Test mock strategy state update."""
        strategy = MockStrategy()
        event = Mock(spec=NostrEvent)
        current_time = 1234.5

        strategy.update_state(event, current_time)

        assert len(strategy.update_calls) == 1
        assert strategy.update_calls[0] == (event, current_time)

    def test_abstract_base_class_cannot_be_instantiated(self) -> None:
        """Test that AntiSpamStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AntiSpamStrategy("test")  # type: ignore
