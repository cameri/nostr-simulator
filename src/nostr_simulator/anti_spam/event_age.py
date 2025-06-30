"""Event Age Proof anti-spam strategy implementation."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from ..protocol.events import NostrEvent
from .base import AntiSpamStrategy, StrategyResult


@dataclass
class AgeProof:
    """Proof that an event was created at a specific time."""

    timestamp: float
    proof: bytes
    difficulty: int
    key_age: float  # Age of the key in seconds


class EventAgeStrategy(AntiSpamStrategy):
    """Event Age Proof anti-spam strategy.

    This strategy validates event timestamps and implements age-based filtering
    to prevent spam attacks using very old or future events.
    """

    def __init__(
        self,
        max_future_drift: float = 600.0,  # 10 minutes
        max_past_age: float = 86400.0,  # 24 hours
        chronological_validation: bool = True,
        age_proof_required: bool = False,
        min_key_age: float = 3600.0,  # 1 hour minimum key age
        age_proof_difficulty: int = 4,  # Leading zero bits required for age proof
    ) -> None:
        """Initialize the Event Age strategy.

        Args:
            max_future_drift: Maximum seconds into the future an event can be.
            max_past_age: Maximum age of events in seconds.
            chronological_validation: Whether to enforce chronological ordering.
            age_proof_required: Whether to require cryptographic age proofs.
            min_key_age: Minimum required age for keys in seconds.
            age_proof_difficulty: Difficulty for age proof generation.
        """
        super().__init__("event_age")

        self.max_future_drift = max_future_drift
        self.max_past_age = max_past_age
        self.chronological_validation = chronological_validation
        self.age_proof_required = age_proof_required
        self.min_key_age = min_key_age
        self.age_proof_difficulty = age_proof_difficulty

        # Track key creation times
        self._key_first_seen: dict[str, float] = {}
        # Track last event time per key for chronological validation
        self._last_event_time: dict[str, float] = {}

        self._metrics = {
            "events_processed": 0,
            "future_events_rejected": 0,
            "old_events_rejected": 0,
            "chronological_violations": 0,
            "age_proof_failures": 0,
            "young_key_rejections": 0,
        }

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event using age-based validation.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event is allowed and why.
        """
        start_time = time.time()
        self._metrics["events_processed"] += 1

        # Basic timestamp validation
        timestamp_result = self._validate_timestamp(event, current_time)
        if not timestamp_result["valid"]:
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason=timestamp_result["reason"],
                metrics={"validation_type": "timestamp"},
                computational_cost=computational_cost,
            )

        # Chronological validation
        if self.chronological_validation:
            chronological_result = self._validate_chronological_order(event)
            if not chronological_result["valid"]:
                self._metrics["chronological_violations"] += 1
                computational_cost = time.time() - start_time
                return StrategyResult(
                    allowed=False,
                    reason=chronological_result["reason"],
                    metrics={"validation_type": "chronological"},
                    computational_cost=computational_cost,
                )

        # Key age validation
        key_age_result = self._validate_key_age(event, current_time)
        if not key_age_result["valid"]:
            self._metrics["young_key_rejections"] += 1
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason=key_age_result["reason"],
                metrics={
                    "validation_type": "key_age",
                    "key_age": key_age_result.get("key_age", 0),
                },
                computational_cost=computational_cost,
            )

        # Age proof validation (if required)
        if self.age_proof_required:
            age_proof_result = self._validate_age_proof(event)
            if not age_proof_result["valid"]:
                self._metrics["age_proof_failures"] += 1
                computational_cost = time.time() - start_time
                return StrategyResult(
                    allowed=False,
                    reason=age_proof_result["reason"],
                    metrics={"validation_type": "age_proof"},
                    computational_cost=computational_cost,
                )

        computational_cost = time.time() - start_time
        return StrategyResult(
            allowed=True,
            reason="Event passed age validation",
            metrics={
                "validation_type": "age_valid",
                "event_age": current_time - event.created_at,
                "key_age": key_age_result.get("key_age", 0),
            },
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        # Track key first seen time
        if event.pubkey not in self._key_first_seen:
            self._key_first_seen[event.pubkey] = current_time

        # Update last event time for chronological validation
        if self.chronological_validation:
            self._last_event_time[event.pubkey] = event.created_at

    def _validate_timestamp(
        self, event: NostrEvent, current_time: float
    ) -> dict[str, Any]:
        """Validate event timestamp against drift limits.

        Args:
            event: The event to validate.
            current_time: Current simulation time.

        Returns:
            Dictionary with validation result and reason.
        """
        event_age = current_time - event.created_at

        # Check for future events
        if event_age < -self.max_future_drift:
            self._metrics["future_events_rejected"] += 1
            return {
                "valid": False,
                "reason": f"Event too far in future: {-event_age:.1f}s ahead",
                "drift": -event_age,
            }

        # Check for very old events
        if event_age > self.max_past_age:
            self._metrics["old_events_rejected"] += 1
            return {
                "valid": False,
                "reason": f"Event too old: {event_age:.1f}s old",
                "age": event_age,
            }

        return {
            "valid": True,
            "reason": "Timestamp within acceptable range",
            "age": event_age,
        }

    def _validate_chronological_order(self, event: NostrEvent) -> dict[str, Any]:
        """Validate that events from a key are in chronological order.

        Args:
            event: The event to validate.

        Returns:
            Dictionary with validation result and reason.
        """
        if event.pubkey in self._last_event_time:
            last_time = self._last_event_time[event.pubkey]
            if event.created_at < last_time:
                return {
                    "valid": False,
                    "reason": f"Event out of chronological order: {event.created_at} < {last_time}",
                    "time_diff": last_time - event.created_at,
                }

        return {
            "valid": True,
            "reason": "Event in chronological order",
        }

    def _validate_key_age(
        self, event: NostrEvent, current_time: float
    ) -> dict[str, Any]:
        """Validate that the key is old enough.

        Args:
            event: The event to validate.
            current_time: Current simulation time.

        Returns:
            Dictionary with validation result and reason.
        """
        if event.pubkey not in self._key_first_seen:
            # First time seeing this key
            key_age = 0.0
        else:
            key_age = current_time - self._key_first_seen[event.pubkey]

        if key_age < self.min_key_age:
            return {
                "valid": False,
                "reason": f"Key too young: {key_age:.1f}s < {self.min_key_age:.1f}s",
                "key_age": key_age,
            }

        return {
            "valid": True,
            "reason": f"Key age acceptable: {key_age:.1f}s",
            "key_age": key_age,
        }

    def _validate_age_proof(self, event: NostrEvent) -> dict[str, Any]:
        """Validate cryptographic age proof in the event.

        Args:
            event: The event to validate.

        Returns:
            Dictionary with validation result and reason.
        """
        age_proof = self._extract_age_proof(event)
        if age_proof is None:
            return {
                "valid": False,
                "reason": "No age proof found in event",
            }

        # Verify the age proof
        if not self._verify_age_proof(event, age_proof):
            return {
                "valid": False,
                "reason": "Invalid age proof",
            }

        return {
            "valid": True,
            "reason": "Valid age proof",
            "proof_timestamp": age_proof.timestamp,
            "key_age": age_proof.key_age,
        }

    def _extract_age_proof(self, event: NostrEvent) -> AgeProof | None:
        """Extract age proof from event tags.

        Args:
            event: The event to extract proof from.

        Returns:
            AgeProof if found, None otherwise.
        """
        for tag in event.tags:
            if tag.name == "age_proof" and len(tag.values) >= 1:
                try:
                    proof_data = tag.values[0].split(":")
                    if len(proof_data) >= 4:
                        timestamp = float(proof_data[0])
                        proof = bytes.fromhex(proof_data[1])
                        difficulty = int(proof_data[2])
                        key_age = float(proof_data[3])

                        return AgeProof(
                            timestamp=timestamp,
                            proof=proof,
                            difficulty=difficulty,
                            key_age=key_age,
                        )
                except (ValueError, IndexError):
                    continue

        return None

    def _verify_age_proof(self, event: NostrEvent, age_proof: AgeProof) -> bool:
        """Verify an age proof.

        Args:
            event: The event containing the proof.
            age_proof: The age proof to verify.

        Returns:
            True if the proof is valid, False otherwise.
        """
        # Create the challenge hash
        challenge_data = f"{event.pubkey}:{age_proof.timestamp}:{age_proof.key_age}"
        challenge_hash = hashlib.sha256(challenge_data.encode()).digest()

        # Verify the proof meets the difficulty requirement
        combined = challenge_hash + age_proof.proof
        result_hash = hashlib.sha256(combined).digest()

        # Check leading zero bits
        required_zeros = age_proof.difficulty
        leading_zeros = self._count_leading_zero_bits(result_hash)

        return leading_zeros >= required_zeros

    def _count_leading_zero_bits(self, hash_bytes: bytes) -> int:
        """Count leading zero bits in a hash.

        Args:
            hash_bytes: The hash bytes to count.

        Returns:
            Number of leading zero bits.
        """
        count = 0
        for byte in hash_bytes:
            if byte == 0:
                count += 8
            else:
                # Count zeros in the first non-zero byte
                # Use bit_length to find the position of the highest set bit
                # Then subtract from 8 to get leading zeros in this byte
                leading_zeros_in_byte = 8 - byte.bit_length()
                count += leading_zeros_in_byte
                break
        return count

    def generate_age_proof(
        self, pubkey: str, timestamp: float, key_age: float
    ) -> AgeProof:
        """Generate an age proof for a key.

        Args:
            pubkey: The public key.
            timestamp: The timestamp for the proof.
            key_age: The age of the key in seconds.

        Returns:
            Generated age proof.
        """
        challenge_data = f"{pubkey}:{timestamp}:{key_age}"
        challenge_hash = hashlib.sha256(challenge_data.encode()).digest()

        # Find a proof that meets the difficulty requirement
        nonce = 0
        while True:
            proof = nonce.to_bytes(8, "big")
            combined = challenge_hash + proof
            result_hash = hashlib.sha256(combined).digest()

            if self._count_leading_zero_bits(result_hash) >= self.age_proof_difficulty:
                return AgeProof(
                    timestamp=timestamp,
                    proof=proof,
                    difficulty=self.age_proof_difficulty,
                    key_age=key_age,
                )

            nonce += 1
            if nonce > 10**6:  # Prevent infinite loops
                raise RuntimeError(
                    "Failed to generate age proof within reasonable time"
                )


class TimestampVerificationStrategy(AntiSpamStrategy):
    """Simple timestamp verification strategy.

    This is a lightweight version that only validates timestamps
    without requiring cryptographic proofs.
    """

    def __init__(
        self,
        max_future_drift: float = 300.0,  # 5 minutes
        max_past_age: float = 3600.0,  # 1 hour
    ) -> None:
        """Initialize the timestamp verification strategy.

        Args:
            max_future_drift: Maximum seconds into the future an event can be.
            max_past_age: Maximum age of events in seconds.
        """
        super().__init__("timestamp_verification")

        self.max_future_drift = max_future_drift
        self.max_past_age = max_past_age

        self._metrics = {
            "events_processed": 0,
            "future_events_rejected": 0,
            "old_events_rejected": 0,
        }

    def evaluate_event(self, event: NostrEvent, current_time: float) -> StrategyResult:
        """Evaluate event timestamp.

        Args:
            event: The event to evaluate.
            current_time: Current simulation time.

        Returns:
            StrategyResult indicating if the event is allowed and why.
        """
        start_time = time.time()
        self._metrics["events_processed"] += 1

        event_age = current_time - event.created_at

        # Check for future events
        if event_age < -self.max_future_drift:
            self._metrics["future_events_rejected"] += 1
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason=f"Event too far in future: {-event_age:.1f}s ahead",
                metrics={"drift": -event_age},
                computational_cost=computational_cost,
            )

        # Check for very old events
        if event_age > self.max_past_age:
            self._metrics["old_events_rejected"] += 1
            computational_cost = time.time() - start_time
            return StrategyResult(
                allowed=False,
                reason=f"Event too old: {event_age:.1f}s old",
                metrics={"age": event_age},
                computational_cost=computational_cost,
            )

        computational_cost = time.time() - start_time
        return StrategyResult(
            allowed=True,
            reason="Timestamp valid",
            metrics={"age": event_age},
            computational_cost=computational_cost,
        )

    def update_state(self, event: NostrEvent, current_time: float) -> None:
        """Update state after processing event.

        Args:
            event: The processed event.
            current_time: Current simulation time.
        """
        # No state to update for simple timestamp verification
        pass
