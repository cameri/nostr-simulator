"""Base classes for anti-spam strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent


@dataclass
class StrategyResult:
    """Result of applying an anti-spam strategy."""

    allowed: bool
    reason: str
    metrics: dict[str, Any] | None = None
    computational_cost: float = 0.0  # Time in seconds


class AntiSpamStrategy(ABC):
    """Abstract base class for anti-spam strategies."""

    def __init__(self, name: str) -> None:
        """Initialize the strategy.

        Args:
            name: Name of the strategy.
        """
        self.name = name
        self._metrics: dict[str, Any] = {}

    @abstractmethod
    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate if an event should be allowed based on this strategy.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event is allowed and why.
        """
        pass

    @abstractmethod
    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update internal state after processing an event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        pass

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for this strategy.

        Returns:
            Dictionary of metrics.
        """
        return self._metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
