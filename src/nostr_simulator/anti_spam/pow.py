"""Proof of Work anti-spam strategy implementation."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


class ProofOfWorkStrategy(AntiSpamStrategy):
    """Proof of Work anti-spam strategy.

    This strategy requires events to include a proof of work by having
    a certain number of leading zero bits in their event ID hash.
    """

    def __init__(
        self,
        min_difficulty: int = 8,
        max_difficulty: int = 24,
        target_solve_time: float = 5.0,
        adjustment_period: int = 2016,  # Bitcoin-style adjustment period
        adaptive: bool = True,
    ) -> None:
        """Initialize the Proof of Work strategy.

        Args:
            min_difficulty: Minimum required difficulty (leading zero bits).
            max_difficulty: Maximum allowed difficulty.
            target_solve_time: Target time in seconds to solve a PoW.
            adjustment_period: Number of events between difficulty adjustments.
            adaptive: Whether to adaptively adjust difficulty.
        """
        super().__init__("proof_of_work")

        self.min_difficulty = min_difficulty
        self.max_difficulty = max_difficulty
        self.target_solve_time = target_solve_time
        self.adjustment_period = adjustment_period
        self.adaptive = adaptive
        self.current_difficulty = min_difficulty

        # Tracking for difficulty adjustment
        self._event_times: list[float] = []
        self._last_adjustment_time = 0.0

        # Initialize metrics
        self._metrics = {
            "events_processed": 0,
            "total_difficulty": 0,
            "avg_difficulty": 0.0,
            "current_difficulty": self.current_difficulty,
            "difficulty_adjustments": 0,
        }

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate if an event meets the PoW requirement.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event has sufficient PoW.
        """
        event_difficulty = self._calculate_pow_difficulty(event)

        if event_difficulty >= self.current_difficulty:
            return StrategyResult(
                allowed=True,
                reason=f"PoW valid (difficulty: {event_difficulty}, required: {self.current_difficulty})",
                metrics={"pow_difficulty": event_difficulty},
                computational_cost=0.0,  # Validation is very fast
            )
        else:
            return StrategyResult(
                allowed=False,
                reason=f"Insufficient PoW (difficulty: {event_difficulty}, required: {self.current_difficulty})",
                metrics={"pow_difficulty": event_difficulty},
                computational_cost=0.0,
            )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update internal state after processing an event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        event_difficulty = self._calculate_pow_difficulty(event)

        # Update metrics
        self._metrics["events_processed"] += 1
        self._metrics["total_difficulty"] += event_difficulty
        self._metrics["avg_difficulty"] = (
            self._metrics["total_difficulty"] / self._metrics["events_processed"]
        )
        self._metrics["current_difficulty"] = self.current_difficulty

        # Track event times for difficulty adjustment
        if self.adaptive:
            self._event_times.append(current_time)

            # Check if it's time to adjust difficulty
            if len(self._event_times) >= self.adjustment_period:
                self._perform_difficulty_adjustment()

    def _calculate_pow_difficulty(self, event: NostrEvent) -> int:
        """Calculate the proof of work difficulty for an event.

        Args:
            event: The event to analyze.

        Returns:
            Number of leading zero bits in the event ID.
        """
        difficulty = 0
        for char in event.id:
            if char == "0":
                difficulty += 4  # Each hex zero is 4 bits
            else:
                # Count leading zeros in the binary representation of this hex digit
                hex_value = int(char, 16)
                for i in range(4):
                    if (hex_value >> (3 - i)) & 1 == 0:
                        difficulty += 1
                    else:
                        break
                break
        return difficulty

    def _perform_difficulty_adjustment(self) -> None:
        """Perform difficulty adjustment based on recent solve times."""
        if len(self._event_times) < 2:
            return

        # Calculate average time between events over the adjustment period
        time_span = self._event_times[-1] - self._event_times[0]
        avg_solve_time = time_span / (len(self._event_times) - 1)

        self._adjust_difficulty(avg_solve_time)

        # Reset tracking
        self._event_times = [self._event_times[-1]]  # Keep last timestamp
        self._metrics["difficulty_adjustments"] += 1

    def _adjust_difficulty(self, avg_solve_time: float) -> None:
        """Adjust difficulty based on average solve time.

        Args:
            avg_solve_time: Average time between events.
        """
        if avg_solve_time < self.target_solve_time * 0.8:
            # Events are being solved too quickly, increase difficulty
            self.current_difficulty = min(
                self.current_difficulty + 1, self.max_difficulty
            )
        elif avg_solve_time > self.target_solve_time * 1.2:
            # Events are being solved too slowly, decrease difficulty
            self.current_difficulty = max(
                self.current_difficulty - 1, self.min_difficulty
            )

    def mine_nonce_for_difficulty(
        self,
        event_data: dict[str, Any],
        target_difficulty: int,
        timeout: float = 30.0,
        max_attempts: int = 1_000_000,  # Limit maximum attempts
    ) -> tuple[int, int, float]:
        """Mine a nonce to achieve target difficulty.

        This is a utility method for testing and simulation of PoW mining.

        Args:
            event_data: Base event data to mine on.
            target_difficulty: Target number of leading zero bits.
            timeout: Maximum time to spend mining (seconds).
            max_attempts: Maximum number of nonces to try.

        Returns:
            Tuple of (nonce, actual_difficulty, solve_time).

        Raises:
            TimeoutError: If timeout is reached before finding solution.
            ValueError: If max attempts reached without solution.
        """
        start_time = time.time()
        nonce = 0
        last_timeout_check = start_time

        while nonce < max_attempts:
            # Add nonce to event data
            mining_data = event_data.copy()
            mining_data["nonce"] = nonce

            # Calculate event ID
            json_str = json.dumps(
                [
                    0,  # Reserved
                    mining_data.get("pubkey", ""),
                    mining_data.get("created_at", 0),
                    mining_data.get("kind", 0),
                    mining_data.get("tags", []),
                    mining_data.get("content", ""),
                ],
                separators=(",", ":"),
                ensure_ascii=False,
            )

            event_id = hashlib.sha256(json_str.encode()).hexdigest()
            difficulty = self._calculate_pow_difficulty_from_id(event_id)

            if difficulty >= target_difficulty:
                solve_time = time.time() - start_time
                return nonce, difficulty, solve_time

            nonce += 1

            # Check timeout every 1000 attempts to avoid excessive time.time() calls
            current_time = time.time()
            if nonce % 1000 == 0 or current_time - last_timeout_check > 1.0:
                if current_time - start_time > timeout:
                    raise TimeoutError(
                        f"Failed to find nonce for difficulty {target_difficulty} within {timeout}s"
                    )
                last_timeout_check = current_time

        # Max attempts reached
        raise ValueError(
            f"Failed to find nonce for difficulty {target_difficulty} within {max_attempts} attempts"
        )

    def _calculate_pow_difficulty_from_id(self, event_id: str) -> int:
        """Calculate PoW difficulty from an event ID string.

        Args:
            event_id: Hex string event ID.

        Returns:
            Number of leading zero bits.
        """
        difficulty = 0
        for char in event_id:
            if char == "0":
                difficulty += 4
            else:
                hex_value = int(char, 16)
                for i in range(4):
                    if (hex_value >> (3 - i)) & 1 == 0:
                        difficulty += 1
                    else:
                        break
                break
        return difficulty
